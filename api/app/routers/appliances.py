from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.db import get_supabase
from app.deps import OwnedAppliance, OwnedHome
from app.schemas import ApplianceIn, ApplianceOut, AppliancePatch
from app.services.appliances import (
    appliance_output,
    get_catalog,
    prepare_appliance_data,
)
from app.services.schedules import default_hourly_use

router = APIRouter(tags=["appliances"])
USER_EDITABLE_FIELDS = {
    "type",
    "brand",
    "model",
    "capacity_value",
    "capacity_unit",
    "inverter",
    "watts",
    "duty_factor",
    "surge_factor",
    "qty",
    "hourly_use",
    "hours_per_day",
    "is_essential",
    "room",
}


class ApplianceBulkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ApplianceIn] = Field(min_length=1, max_length=40)


@router.get("/homes/{home_id}/appliances", response_model=list[ApplianceOut])
def list_appliances(home: OwnedHome) -> list[dict]:
    response = (
        get_supabase()
        .table("home_appliances")
        .select("*")
        .eq("home_id", home["id"])
        .order("created_at")
        .execute()
    )
    return [appliance_output(row) for row in (response.data or [])]


@router.post(
    "/homes/{home_id}/appliances",
    response_model=ApplianceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_appliance(home: OwnedHome, payload: ApplianceIn) -> dict:
    row = prepare_appliance_data(payload.model_dump(), home["id"], get_catalog())
    response = get_supabase().table("home_appliances").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Appliance could not be created")
    return appliance_output(response.data[0])


@router.post(
    "/homes/{home_id}/appliances/bulk",
    response_model=list[ApplianceOut],
    status_code=status.HTTP_201_CREATED,
)
def create_appliances_bulk(home: OwnedHome, payload: ApplianceBulkIn) -> list[dict]:
    rows = [
        prepare_appliance_data(item.model_dump(), home["id"], get_catalog())
        for item in payload.items
    ]
    response = get_supabase().table("home_appliances").insert(rows).execute()
    return [appliance_output(row) for row in (response.data or [])]


@router.patch("/appliances/{appliance_id}", response_model=ApplianceOut)
def patch_appliance(
    appliance: OwnedAppliance, payload: AppliancePatch
) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    changed = USER_EDITABLE_FIELDS.intersection(updates)
    if "hours_per_day" in updates:
        hours = updates.pop("hours_per_day")
        if "hourly_use" not in updates:
            updated_type = updates.get("type", appliance["type"])
            updates["hourly_use"] = default_hourly_use(updated_type, hours)
    for protected_field in ("source_tag", "confidence", "user_verified", "image_path"):
        updates.pop(protected_field, None)
    if changed:
        updates["source_tag"] = "user"
        updates["user_verified"] = True
    if not updates:
        return appliance_output(appliance)

    updates["updated_at"] = datetime.now(UTC).isoformat()
    response = (
        get_supabase()
        .table("home_appliances")
        .update(updates)
        .eq("id", appliance["id"])
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Appliance not found")
    return appliance_output(response.data[0])


@router.delete(
    "/appliances/{appliance_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_appliance(appliance: OwnedAppliance) -> None:
    get_supabase().table("home_appliances").delete().eq("id", appliance["id"]).execute()
