from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.datastructures import UploadFile
from starlette.concurrency import run_in_threadpool

from app.db import get_supabase
from app.deps import AuthenticatedUser, OwnedHome, get_owned_home
from app.services.bill_ocr import BillOCRError, parse_bill_text, read_bill_image
from app.services.calibration import (
    estimate_monthly_kwh,
    calibration_verdict,
    monthly_index,
    overall_calibration_ratio,
    suggest_scaling,
)
from app.services.image_rate_limit import enforce_image_rate_limit

router = APIRouter(prefix="/homes", tags=["bills"])
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class BillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: date
    units_kwh: float = Field(ge=0, le=5000)

    @field_validator("month")
    @classmethod
    def normalize_month(cls, value: date) -> date:
        month = value.replace(day=1)
        if month > date.today().replace(day=1):
            raise ValueError("Billing month cannot be in the future")
        return month


@router.post("/{home_id}/bill")
async def create_bill_preview(
    home: OwnedHome,
    user: AuthenticatedUser,
    request: Request,
) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("application/json"):
        try:
            payload = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid JSON payload") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="Provide a bill object")
        if "raw_text" in payload:
            parsed = parse_bill_text(str(payload["raw_text"]))
            return {"parsed": parsed}
        try:
            bill = BillInput.model_validate(payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        parsed = {
            "units_kwh": bill.units_kwh,
            "month": bill.month.isoformat(),
            "history": [],
            "amount_pkr": None,
            "disco": None,
            "confidence": 1.0,
            "raw_text": "",
            "warnings": [],
        }
        return {"parsed": parsed}

    if not content_type.startswith("multipart/form-data"):
        raise HTTPException(
            status_code=415,
            detail="Use JSON bill details or multipart form data with an image",
        )
    form = await request.form()
    image = form.get("image")
    if not isinstance(image, UploadFile):
        raise HTTPException(status_code=422, detail="Provide a bill image")
    if str(form.get("consent", "")).lower() != "true":
        raise HTTPException(
            status_code=422,
            detail="Confirm that the bill image may be sent to Google Gemini for reading",
        )
    enforce_image_rate_limit(user["id"])
    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Bill image must be 8 MB or smaller")
    try:
        parsed = await run_in_threadpool(
            read_bill_image, image_bytes, image.content_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except BillOCRError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await image.close()
    return {"parsed": parsed}


@router.post("/{home_id}/bills")
def save_bill(home: OwnedHome, payload: BillInput, user: AuthenticatedUser) -> dict[str, Any]:
    response = (
        get_supabase()
        .table("bills")
        .upsert(
            {
                "home_id": home["id"],
                "month": payload.month.isoformat(),
                "units_kwh": payload.units_kwh,
                "raw": payload.model_dump(mode="json"),
            },
            on_conflict="home_id,month",
        )
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Bill could not be saved")
    return response.data[0]


@router.get("/{home_id}/bills")
def list_bills(home: OwnedHome, user: AuthenticatedUser) -> list[dict[str, Any]]:
    response = (
        get_supabase()
        .table("bills")
        .select("*")
        .eq("home_id", home["id"])
        .order("month", desc=True)
        .execute()
    )
    return response.data or []


@router.get("/{home_id}/calibration")
def get_calibration(home: OwnedHome, user: AuthenticatedUser) -> dict[str, Any]:
    client = get_supabase()
    response = (
        client
        .table("bills")
        .select("id, units_kwh, month")
        .eq("home_id", home["id"])
        .order("month")
        .execute()
    )
    bills = response.data or []
    appliance_response = (
        client.table("home_appliances")
        .select("*")
        .eq("home_id", home["id"])
        .execute()
    )
    appliances = appliance_response.data or []
    estimated_monthly_kwh = estimate_monthly_kwh(appliances)
    if not bills or estimated_monthly_kwh <= 0:
        return {
            "estimated_monthly_kwh": round(estimated_monthly_kwh, 2),
            "bill_monthly_kwh": float(bills[-1]["units_kwh"]) if bills else None,
            "ratio": None,
            "band": "add a bill and appliance data" if not bills or not appliances else "unavailable",
            "reasons": [],
            "proposals": [],
            "monthly_index": None,
        }
    units_history = [float(bill["units_kwh"]) for bill in bills]
    ratio = overall_calibration_ratio(units_history, estimated_monthly_kwh)
    if ratio is None:
        raise HTTPException(status_code=500, detail="Could not calculate bill calibration")
    verdict = calibration_verdict(ratio)
    return {
        "estimated_monthly_kwh": round(estimated_monthly_kwh, 2),
        "bill_monthly_kwh": float(bills[-1]["units_kwh"]),
        **verdict,
        "proposals": suggest_scaling(appliances, ratio),
        "monthly_index": monthly_index(units_history),
    }


@router.delete("/bills/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(bill_id: str, user: AuthenticatedUser) -> None:
    response = (
        get_supabase()
        .table("bills")
        .select("id, home_id")
        .eq("id", bill_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Bill not found")
    get_owned_home(response.data[0]["home_id"], user)
    get_supabase().table("bills").delete().eq("id", bill_id).execute()
