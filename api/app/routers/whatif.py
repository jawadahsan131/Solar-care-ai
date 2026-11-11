from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.db import get_supabase
from app.deps import AuthenticatedUser, OwnedHome
from app.services.tariff import load_tariff
from app.services.weather import climate_normal
from app.services.whatif import compare_scenarios

router = APIRouter(prefix="/homes", tags=["what-if"])


class WhatIfInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    panel_kw: float = Field(ge=0, le=100, allow_inf_nan=False)
    battery_kwh: float = Field(default=0, ge=0, le=200, allow_inf_nan=False)
    inverter_kw: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    outage_hours: float = Field(default=0, ge=0, le=24, allow_inf_nan=False)
    cost_per_kw_pkr: float | None = Field(
        default=None, ge=0, le=100_000_000, allow_inf_nan=False
    )


@router.post("/{home_id}/whatif")
def what_if_home(
    payload: WhatIfInput,
    home: OwnedHome,
    user: AuthenticatedUser,
) -> dict[str, Any]:
    if home.get("lat") is None or home.get("lon") is None:
        raise HTTPException(
            status_code=400,
            detail="Set your city in the forecast page before running a what-if estimate.",
        )
    response = (
        get_supabase()
        .table("home_appliances")
        .select("*")
        .eq("home_id", home["id"])
        .execute()
    )
    appliances = response.data or []
    monthly_weather = [
        (
            month,
            climate_normal(
                float(home["lat"]),
                float(home["lon"]),
                date(2025, month, 15),
                str(home.get("city") or ""),
            )[0],
        )
        for month in range(1, 13)
    ]
    return {
        "home_id": home["id"],
        "city": home.get("city"),
        "weather_source": "approximate monthly climate normals",
        "appliance_count": len(appliances),
        "assumptions": [
            "One representative climate-normal day per month, weighted by calendar days.",
            "Demand uses saved appliance schedules; no personal history is applied.",
            "Battery usable capacity is modeled at 80% with 90% round-trip efficiency.",
            "The battery resets at the start of each representative day; no inter-day carryover is modeled.",
            "Outage backup uses essential appliances when marked; otherwise it uses the full modeled load.",
            "Inverter clipping is applied; export compensation is not estimated.",
            "The same user-entered installed cost per kW is used for each scenario.",
        ],
        **compare_scenarios(
            monthly_weather,
            appliances,
            panel_kw=payload.panel_kw,
            battery_kwh=payload.battery_kwh,
            inverter_kw=payload.inverter_kw,
            outage_hours=payload.outage_hours,
            cost_per_kw_pkr=payload.cost_per_kw_pkr,
            tariff=load_tariff(),
        ),
    }
