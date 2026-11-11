from __future__ import annotations

import json
import re
from io import BytesIO
from datetime import date
from typing import Any

import httpx
from google import genai
from google.genai import errors, types
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings

MONTH_ALIASES = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


class BillHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    month: str | None = None
    units_kwh: float | None = Field(default=None, ge=0)


class BillOCRResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    month: str | None = None
    units_kwh: float | None = Field(default=None, ge=0)
    history: list[BillHistoryEntry] = Field(default_factory=list)
    amount_pkr: float | None = Field(default=None, ge=0)
    disco: str | None = None
    raw_text: str | None = None


class BillOCRError(Exception):
    pass


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def _parse_month_value(raw_value: Any) -> date | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, date):
        return raw_value.replace(day=1)
    text = str(raw_value).strip().lower().replace("_", " ")
    if not text or text in {"n/a", "na", "none", "null"}:
        return None

    match = re.search(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*[-/ ]?\s*(\d{4}|\d{2})",
        text,
    )
    if match:
        month = MONTH_ALIASES[match.group(1)]
        year_text = match.group(2)
        year = int(year_text) if len(year_text) == 4 else 2000 + int(year_text)
        try:
            return date(year, month, 1)
        except ValueError:
            return None

    match = re.search(r"(\d{1,2})\s*[/\-]\s*(\d{4})", text)
    if match:
        try:
            return date(int(match.group(2)), int(match.group(1)), 1)
        except ValueError:
            return None

    match = re.search(r"(\d{4})\s*[/\-]\s*(\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), 1)
        except ValueError:
            return None

    return None


def _parse_history_entries(raw_text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pattern = re.compile(
        r"(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(?:[-/\s]*)\s*(?P<year>\d{4}|\d{2})\s*(?:[:=]|\s+)\s*(?P<units>\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(raw_text):
        month_name = match.group("month").lower()
        year_text = match.group("year")
        units = _coerce_float(match.group("units"))
        if units is None:
            continue
        month_num = MONTH_ALIASES.get(month_name)
        if month_num is None:
            continue
        year = int(year_text) if len(year_text) == 4 else 2000 + int(year_text)
        if year > 2100:
            continue
        month_date = date(year, month_num, 1)
        if month_date > date.today().replace(day=1):
            continue
        entries.append({"month": month_date.isoformat(), "units": round(units, 2)})

    deduped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        deduped[entry["month"]] = entry
    return sorted(deduped.values(), key=lambda item: item["month"])


def parse_bill_text(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        return {
            "units_kwh": None,
            "month": None,
            "history": [],
            "amount_pkr": None,
            "disco": None,
            "confidence": 0.0,
            "raw_text": text,
            "warnings": ["No bill text was supplied."],
        }

    warnings: list[str] = []
    history = _parse_history_entries(text)
    explicit_month = None
    for line in text.splitlines():
        lower = line.lower()
        if lower.startswith("month") or "billing month" in lower or "bill month" in lower:
            candidate = line.split(":", 1)[1] if ":" in line else line
            candidate = candidate.split("history", 1)[0].strip()
            parsed = _parse_month_value(candidate)
            if parsed:
                explicit_month = parsed
                break
        if "history" in lower:
            break
    if explicit_month is None:
        for line in text.splitlines():
            lower = line.lower()
            if lower.startswith("month") or "billing month" in lower or "bill month" in lower:
                candidate = line.split(":", 1)[1] if ":" in line else line
                candidate = candidate.split("history", 1)[0].strip()
                parsed = _parse_month_value(candidate)
                if parsed:
                    explicit_month = parsed
                    break
            if "history" in lower:
                break
            for token in re.findall(r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(?:\d{2}|\d{4})|\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}", line, re.IGNORECASE):
                parsed = _parse_month_value(token)
                if parsed:
                    explicit_month = parsed
                    break
            if explicit_month is not None:
                break

    units = None
    current_units_seen = False
    for pattern in [
        r"(?:total\s*)?(?:units|kwh|consumption)\s*(?:used|consumed)?\s*[:=]?\s*(\d+(?:\.\d+)?)",
        r"(?:current\s*)?(?:month\s*)?(?:units|kwh)\s*[:=]?\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:kwh|units)\s*(?:used|consumed)?",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            current_units_seen = True
            units = _coerce_float(match.group(1))
            if units is not None:
                break

    if units is not None and (units < 0 or units > 5000):
        warnings.append("Units value is outside the realistic 0-5000 kWh range; ignoring it.")
        units = None

    month = explicit_month
    if month is None and history:
        month = _parse_month_value(history[-1].get("month"))

    if units is None and history and not current_units_seen:
        units = history[-1].get("units")

    if explicit_month is not None and explicit_month > date.today().replace(day=1):
        warnings.append("Billing month is in the future; ignoring it.")
        month = None

    amount = None
    amount_match = re.search(r"(?:total\s*amount|amount|rs\.|pkr)\s*[:=]?\s*([0-9,]+(?:\.\d+)?)", text, re.IGNORECASE)
    if amount_match:
        amount = _coerce_float(amount_match.group(1))

    disco = None
    disco_match = re.search(r"(LESCO|KE|IESCO|FESCO|PESCO|HQ|K-ELECTRIC)", text, re.IGNORECASE)
    if disco_match:
        disco = disco_match.group(1).upper()

    confidence = 0.55
    if units is not None and month is not None:
        confidence = 0.9
    elif units is not None or month is not None:
        confidence = 0.7
    if not warnings and units is None and month is None:
        warnings.append("Unable to confidently read a bill month or units from the text.")

    return {
        "units_kwh": round(units, 2) if units is not None else None,
        "month": month.isoformat() if month else None,
        "history": history,
        "amount_pkr": round(amount, 2) if amount is not None else None,
        "disco": disco,
        "confidence": round(confidence, 2),
        "raw_text": text,
        "warnings": warnings,
    }


def read_bill_image(image_bytes: bytes, mime: str | None = None) -> dict[str, Any]:
    if not image_bytes:
        raise ValueError("image_bytes cannot be empty")
    if len(image_bytes) > 8 * 1024 * 1024:
        raise ValueError("Bill image must be 8 MB or smaller")
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("Upload a JPEG, PNG, or WebP bill image")
    if not settings.gemini_api_key or not settings.gemini_model:
        raise BillOCRError(
            "Bill photo reading is not configured. Please enter the month and units manually."
        )

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("The uploaded bill image is invalid")
    except (OSError, ValueError) as exc:
        raise ValueError("The uploaded bill image is invalid") from exc

    if max(image.size) > 1600:
        scale = 1600 / max(image.size)
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88, optimize=True)
    prompt = (
        "Read this electricity bill from Pakistan. Return only fields that are "
        "clearly legible; use null for uncertain values and never infer or guess. "
        "Extract current billing month, current units consumed in kWh, any monthly "
        "history rows (month and units), total amount in PKR, electricity company "
        "name, and a short transcription of relevant bill text. Ignore meter "
        "numbers, reference numbers, taxes, and charges when extracting units. "
        "Units must mean energy consumption, not amount due."
    )
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=30_000),
    )
    try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=buffer.getvalue(), mime_type="image/jpeg"
                        ),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=BillOCRResponse,
                        temperature=0,
                    ),
                )
                if not response.text:
                    raise BillOCRError("No bill details could be read from this image")
                decoded = json.loads(response.text)
                parsed = BillOCRResponse.model_validate(decoded)
                break
            except errors.ClientError as exc:
                if getattr(exc, "code", None) == 429:
                    raise BillOCRError(
                        "Bill photo reading is busy. Please enter the bill manually."
                    ) from exc
                if attempt == 1:
                    raise BillOCRError(
                        "Bill photo reading failed. Please enter the bill manually."
                    ) from exc
            except (errors.ServerError, httpx.HTTPError, TimeoutError) as exc:
                if attempt == 1:
                    raise BillOCRError(
                        "Bill photo reading failed. Please enter the bill manually."
                    ) from exc
            except (json.JSONDecodeError, ValueError) as exc:
                raise BillOCRError(
                    "Bill photo reading returned invalid details. Please enter the bill manually."
                ) from exc
        else:
            raise BillOCRError("Bill photo reading failed. Please enter the bill manually.")
    finally:
        client.close()

    warnings: list[str] = []
    current_month = _parse_month_value(parsed.month)
    if current_month and current_month > date.today().replace(day=1):
        current_month = None
        warnings.append("Billing month is in the future; ignoring it.")
    if parsed.month and current_month is None and not warnings:
        warnings.append("Could not confidently read the billing month.")

    units = parsed.units_kwh
    if units is not None and units > 5000:
        units = None
        warnings.append("Units value is outside the realistic 0-5000 kWh range; ignoring it.")

    history: list[dict[str, Any]] = []
    for entry in parsed.history:
        entry_month = _parse_month_value(entry.month)
        entry_units = entry.units_kwh
        if (
            entry_month is None
            or entry_month > date.today().replace(day=1)
            or entry_units is None
            or entry_units > 5000
        ):
            warnings.append("An unreadable or impossible history row was ignored.")
            continue
        history.append(
            {"month": entry_month.isoformat(), "units": round(entry_units, 2)}
        )

    confidence = 0.9 if current_month and units is not None else (
        0.7 if current_month or units is not None else 0.4
    )
    if current_month is None and units is None:
        warnings.append("Please check the bill manually before saving.")
    return {
        "units_kwh": round(units, 2) if units is not None else None,
        "month": current_month.isoformat() if current_month else None,
        "history": history,
        "amount_pkr": round(parsed.amount_pkr, 2) if parsed.amount_pkr is not None else None,
        "disco": parsed.disco,
        "confidence": confidence,
        "raw_text": parsed.raw_text or "",
        "warnings": warnings,
    }
