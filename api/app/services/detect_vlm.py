import json
import re
from io import BytesIO
from typing import Any

import httpx
from google import genai
from google.genai import errors, types
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings


class DetectionError(Exception):
    pass


class RawDetectedItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str = "other"
    brand: str | None = None
    model: str | None = None
    capacity_text: str | None = None
    inverter_text: str | None = None
    rated_power_text: str | None = None
    label_text: str | None = None
    count: int = Field(default=1, ge=1, le=50)
    confidence: float = Field(default=0.5, ge=0, le=1)
    notes: str | None = None
    bbox: list[float] | None = None


def resize_for_detection(image_bytes: bytes, max_side: int, quality: int) -> bytes:
    """Apply EXIF rotation and return a resized JPEG without retaining metadata."""
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (OSError, ValueError) as exc:
        raise DetectionError("The uploaded image could not be read") from exc

    longest_side = max(image.size)
    if longest_side > max_side:
        scale = max_side / longest_side
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True)
    return output.getvalue()


def detect_vlm(image_bytes: bytes, mime: str) -> list[dict[str, Any]]:
    """Call Gemini with a structured appliance-detection response."""
    if not settings.gemini_api_key:
        raise DetectionError("Photo detection is not configured; please add items manually")
    if not settings.gemini_model:
        raise DetectionError("Photo detection model is not configured")

    jpeg_bytes = resize_for_detection(image_bytes, max_side=1280, quality=85)
    prompt = (
        "You are inspecting a photo taken inside a home in Pakistan. List every "
        "electrical appliance that is clearly visible. Return a JSON array matching "
        "the supplied schema. Allowed appliance type slugs are: ac, ceiling_fan, "
        "pedestal_fan, exhaust_fan, air_cooler, refrigerator, deep_freezer, "
        "microwave, electric_oven, water_dispenser, electric_kettle, washing_machine, "
        "iron, geyser, water_pump, tv, desktop_pc, laptop, router, ups, led_bulb, "
        "tube_light, phone_charger, vacuum_cleaner, other. Only report brand, model, "
        "capacity, inverter status, or power if readable in the image. Never guess "
        "brand or wattage; use null when unreadable. Copy visible label text exactly. "
        "Combine clearly identical visible units into one item with a count. Ignore "
        "people, furniture, and non-electrical objects. Use other when type is "
        "uncertain and explain in notes. Confidence must honestly reflect certainty."
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
                        types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=list[RawDetectedItem],
                        temperature=0,
                    ),
                )
                text = response.text
                if not text:
                    raise DetectionError("Detection returned no appliance details")
                decoded = json.loads(text)
                if not isinstance(decoded, list):
                    raise DetectionError("Detection returned an invalid response")
                return [
                    RawDetectedItem.model_validate(item).model_dump()
                    for item in decoded
                ]
            except errors.ClientError as exc:
                if getattr(exc, "code", None) == 429:
                    raise DetectionError(
                        "Detection service is busy, please try again or add items manually"
                    ) from exc
                if attempt == 1:
                    raise DetectionError(
                        "Photo detection failed; please try again or add items manually"
                    ) from exc
            except (errors.ServerError, httpx.HTTPError, TimeoutError) as exc:
                if attempt == 1:
                    raise DetectionError(
                        "Photo detection failed; please try again or add items manually"
                    ) from exc
            except (json.JSONDecodeError, ValueError) as exc:
                raise DetectionError("Detection returned an invalid response") from exc
    finally:
        client.close()

    raise DetectionError("Photo detection failed; please try again or add items manually")
