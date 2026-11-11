from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db import get_supabase
from app.deps import AuthenticatedUser, OwnedHome
from app.schemas import ALLOWED_TYPES
from app.services.anomaly import verdicts_for_history
from app.services.demand import (
    demand_components,
    fit_personal_scales,
    predict_demand,
)
from app.services.home_demand import (
    bill_scale as _bill_scale,
    home_appliances as _home_appliances,
    load_model as _load_model,
    predict_home_demand,
    reference_degree_hours as _reference_degree_hours,
    weather_for_home as _weather_for,
)
from app.services.part2_config import MIN_DAYS_FOR_PERSONAL_FIT

router = APIRouter(prefix="/homes", tags=["check-ins"])
LOCAL_TZ = ZoneInfo("Asia/Karachi")


class CheckinInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    ac_hours: float | None = Field(default=None, ge=0, le=24)
    outage_hours: float | None = Field(default=None, ge=0, le=24)
    guests: bool | None = None
    meter_kwh: float | None = Field(default=None, ge=0, le=5000)
    appliance_hours: dict[str, float] | None = None

    @field_validator("appliance_hours")
    @classmethod
    def validate_appliance_hours(
        cls, value: dict[str, float] | None
    ) -> dict[str, float] | None:
        if value is not None:
            if any(key not in ALLOWED_TYPES for key in value):
                raise ValueError("appliance_hours contains an unsupported appliance type")
            if any(not 0 <= hours <= 24 for hours in value.values()):
                raise ValueError("appliance hours must be between 0 and 24")
        return value

    @model_validator(mode="after")
    def validate_date_window(self) -> "CheckinInput":
        today = datetime.now(LOCAL_TZ).date()
        if self.date > today:
            raise ValueError("Check-in date cannot be in the future")
        if self.date < today - timedelta(days=7):
            raise ValueError("Check-ins can only be backfilled for the past 7 days")
        return self


def _save_personal_fit(
    home_id: str,
    appliance_rows: list[dict[str, Any]],
    logs: list[dict[str, Any]],
    cdh_reference: float,
    hdh_reference: float,
) -> dict[str, Any] | None:
    observations = []
    for row in logs:
        weather = row.get("weather") or {}
        hourly = weather.get("hourly")
        if row.get("meter_kwh") is None or not isinstance(hourly, dict):
            continue
        context = {
            "ac_hours": row.get("ac_hours"),
            "outage_hours": row.get("outage_hours"),
            "guests": row.get("guests"),
            "appliance_hours": row.get("appliance_hours") or {},
        }
        parts = demand_components(
            appliance_rows,
            hourly,
            cdh_reference=cdh_reference,
            hdh_reference=hdh_reference,
            context=context,
        )
        observations.append(
            {
                "fixed_kwh": parts["fixed_kwh"],
                "comfort_kwh": parts["comfort_kwh"],
                "actual_kwh": float(row["meter_kwh"]),
            }
        )
    if len(observations) < MIN_DAYS_FOR_PERSONAL_FIT:
        return None
    fitted = fit_personal_scales(observations)
    client = get_supabase()
    saved = (
        client.table("demand_models")
        .upsert(
            {
                "home_id": home_id,
                "params": {"s_ac": fitted["s_ac"], "s_other": fitted["s_other"]},
                "n_days": fitted["n_days"],
                "metrics": {"residual_std": fitted["residual_std"]},
                "fitted_at": datetime.now(LOCAL_TZ).isoformat(),
            },
            on_conflict="home_id",
        )
        .execute()
    )
    if not saved.data:
        raise HTTPException(status_code=500, detail="Demand model could not be updated")
    return fitted


@router.post("/{home_id}/checkin")
async def save_checkin(
    home: OwnedHome,
    user: AuthenticatedUser,
    payload: CheckinInput,
) -> dict[str, Any]:
    appliance_rows = _home_appliances(home["id"])
    weather = await _weather_for(home, payload.date)
    reference_cdh, reference_hdh = await _reference_degree_hours(home)
    existing_logs = (
        get_supabase()
        .table("daily_logs")
        .select("id,log_date,source")
        .eq("home_id", home["id"])
        .gte("log_date", (payload.date - timedelta(days=90)).isoformat())
        .lte("log_date", datetime.now(LOCAL_TZ).date().isoformat())
        .execute()
    )
    n_days = sum(
        1 for row in existing_logs.data or [] if row.get("source", "user") == "user"
    )
    model = _load_model(home["id"])
    params = (model.get("params") or {}) if model else {}
    is_personally_fitted = bool(model and int(model.get("n_days") or 0) >= MIN_DAYS_FOR_PERSONAL_FIT)
    prediction = predict_demand(
        appliance_rows,
        weather["hourly"],
        cdh_reference=reference_cdh,
        hdh_reference=reference_hdh,
        context={
            "ac_hours": payload.ac_hours,
            "outage_hours": payload.outage_hours,
            "guests": payload.guests,
            "appliance_hours": payload.appliance_hours or {},
            "comfort_scale": params.get("s_ac", 1.0) if is_personally_fitted else 1.0,
            "fixed_scale": params.get("s_other", 1.0) if is_personally_fitted else 1.0,
            "global_scale": 1.0 if is_personally_fitted else _bill_scale(home["id"], appliance_rows),
        },
        n_days=n_days,
        residual_std=(model.get("metrics") or {}).get("residual_std") if model else None,
    )
    stored_weather = {
        "hourly": weather["hourly"],
        "source": weather["source"],
        "stale": weather["stale"],
        "normal_city": weather["normal_city"],
    }
    response = (
        get_supabase()
        .table("daily_logs")
        .upsert(
            {
                "home_id": home["id"],
                "log_date": payload.date.isoformat(),
                "ac_hours": payload.ac_hours,
                "outage_hours": payload.outage_hours,
                "guests": payload.guests,
                "meter_kwh": payload.meter_kwh,
                "appliance_hours": payload.appliance_hours,
                "predicted_kwh": prediction["total_kwh"],
                "weather": stored_weather,
                "source": "user",
            },
            on_conflict="home_id,log_date",
        )
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Check-in could not be saved")

    updated_logs_response = (
        get_supabase()
        .table("daily_logs")
        .select("meter_kwh,weather,ac_hours,outage_hours,guests,appliance_hours,source")
        .eq("home_id", home["id"])
        .eq("source", "user")
        .gte("log_date", (payload.date - timedelta(days=90)).isoformat())
        .lte("log_date", datetime.now(LOCAL_TZ).date().isoformat())
        .order("log_date")
        .execute()
    )
    fitted = _save_personal_fit(
        home["id"],
        appliance_rows,
        updated_logs_response.data or [],
        reference_cdh,
        reference_hdh,
    )
    return {**response.data[0], "model_fit": fitted}


@router.get("/{home_id}/checkins")
def list_checkins(
    home: OwnedHome,
    user: AuthenticatedUser,
    days: int = Query(default=30, ge=1, le=90),
) -> list[dict[str, Any]]:
    cutoff = datetime.now(LOCAL_TZ).date() - timedelta(days=days - 1)
    response = (
        get_supabase()
        .table("daily_logs")
        .select("*")
        .eq("home_id", home["id"])
        .gte("log_date", cutoff.isoformat())
        .order("log_date", desc=True)
        .execute()
    )
    return response.data or []


@router.get("/{home_id}/demand")
async def get_demand(
    home: OwnedHome,
    user: AuthenticatedUser,
    day: date | None = Query(default=None, alias="date"),
) -> dict[str, Any]:
    target_day = day or datetime.now(LOCAL_TZ).date()
    return await predict_home_demand(home, target_day)


@router.get("/{home_id}/verdicts")
def get_verdicts(
    home: OwnedHome,
    user: AuthenticatedUser,
    days: int = Query(default=14, ge=1, le=90),
) -> list[dict[str, Any]]:
    cutoff = datetime.now(LOCAL_TZ).date() - timedelta(days=days - 1)
    response = (
        get_supabase()
        .table("daily_logs")
        .select("log_date,meter_kwh,predicted_kwh,ac_hours,appliance_hours,source")
        .eq("home_id", home["id"])
        .eq("source", "user")
        .gte("log_date", cutoff.isoformat())
        .order("log_date")
        .execute()
    )
    return verdicts_for_history(response.data or [])
