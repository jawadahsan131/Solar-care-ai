from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.db import get_supabase
from app.deps import OwnedHome
from app.schemas import ReportSummary, SizeRequest, SizeResponse
from app.services.appliances import build_load_items, get_catalog
from app.services.sizing import SizingAssumptions, size_system

router = APIRouter(tags=["sizing"])


@router.post(
    "/homes/{home_id}/size",
    response_model=SizeResponse,
    status_code=status.HTTP_201_CREATED,
)
def size_home(home: OwnedHome, payload: SizeRequest) -> dict[str, Any]:
    client = get_supabase()
    appliance_response = (
        client.table("home_appliances")
        .select("*")
        .eq("home_id", home["id"])
        .execute()
    )
    appliance_rows = appliance_response.data or []
    if not appliance_rows:
        raise HTTPException(
            status_code=422,
            detail="Add at least one appliance first",
        )

    assumptions_data = SizingAssumptions().model_dump()
    if payload.assumptions:
        assumptions_data.update(payload.assumptions)
    assumptions = SizingAssumptions.model_validate(assumptions_data)
    load_items = build_load_items(appliance_rows, get_catalog())
    result = size_system(load_items, assumptions)
    created_at = datetime.now(UTC).isoformat()
    stored = (
        client.table("sizing_reports")
        .insert(
            {
                "home_id": home["id"],
                "input": {
                    "items": [item.model_dump() for item in load_items],
                    "assumptions": assumptions.model_dump(),
                },
                "result": result.model_dump(),
            }
        )
        .execute()
    )
    if not stored.data:
        raise HTTPException(status_code=500, detail="Sizing report could not be saved")
    report = stored.data[0]
    return {
        "report_id": report["id"],
        "created_at": report.get("created_at", created_at),
        "result": result.model_dump(),
    }


@router.get("/homes/{home_id}/reports", response_model=list[ReportSummary])
def list_reports(home: OwnedHome) -> list[dict]:
    response = (
        get_supabase()
        .table("sizing_reports")
        .select("id,created_at,result")
        .eq("home_id", home["id"])
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    summaries = []
    for report in response.data or []:
        result = report.get("result") or {}
        summaries.append(
            {
                "id": report["id"],
                "created_at": report["created_at"],
                "daily_kwh": result.get("daily_kwh", 0),
                "peak_kw": result.get("peak_kw", 0),
                "options": result.get("options", []),
            }
        )
    return summaries
