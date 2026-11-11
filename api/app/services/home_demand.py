from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException

from app.db import get_supabase
from app.services.calibration import estimate_monthly_kwh, overall_calibration_ratio
from app.services.demand import predict_demand
from app.services.part2_config import MIN_DAYS_FOR_PERSONAL_FIT
from app.services.solar import cdh, hdh
from app.services.weather import get_weather_days


def neutral_weather() -> dict[str, list[float]]:
    return {
        "temp_c": [25.0] * 24,
        "humidity_pct": [50.0] * 24,
        "cloud_pct": [50.0] * 24,
        "ghi_wm2": [0.0] * 24,
    }


async def weather_for_home(home: dict[str, Any], day: date) -> dict[str, Any]:
    if home.get("lat") is None or home.get("lon") is None:
        return {
            "day": day.isoformat(),
            "hourly": neutral_weather(),
            "source": "normal",
            "stale": False,
            "normal_city": None,
        }
    try:
        return (
            await get_weather_days(
                float(home["lat"]),
                float(home["lon"]),
                [day],
                str(home.get("city") or ""),
            )
        )[0]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def reference_degree_hours(home: dict[str, Any]) -> tuple[float, float]:
    if home.get("lat") is None or home.get("lon") is None:
        return 0.0, 0.0
    try:
        onboarding_day = date.fromisoformat(str(home["created_at"])[:10])
    except (KeyError, TypeError, ValueError):
        return 0.0, 0.0
    reference_days = [onboarding_day - timedelta(days=offset) for offset in range(1, 8)]
    weather_days = await get_weather_days(
        float(home["lat"]),
        float(home["lon"]),
        reference_days,
        str(home.get("city") or ""),
    )
    cdh_values = [cdh(item["hourly"]["temp_c"]) for item in weather_days]
    hdh_values = [hdh(item["hourly"]["temp_c"]) for item in weather_days]
    if not cdh_values:
        return 0.0, 0.0
    return sum(cdh_values) / len(cdh_values), sum(hdh_values) / len(hdh_values)


def home_appliances(home_id: str) -> list[dict[str, Any]]:
    response = (
        get_supabase()
        .table("home_appliances")
        .select("*")
        .eq("home_id", home_id)
        .execute()
    )
    return response.data or []


def load_model(home_id: str) -> dict[str, Any] | None:
    response = (
        get_supabase()
        .table("demand_models")
        .select("params,n_days,metrics")
        .eq("home_id", home_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def bill_scale(home_id: str, appliances: list[dict[str, Any]]) -> float:
    if not appliances:
        return 1.0
    estimated = estimate_monthly_kwh(appliances)
    if estimated <= 0:
        return 1.0
    response = (
        get_supabase()
        .table("bills")
        .select("units_kwh")
        .eq("home_id", home_id)
        .order("month")
        .execute()
    )
    history = [float(row["units_kwh"]) for row in response.data or []]
    ratio = overall_calibration_ratio(history, estimated)
    return min(2.0, max(0.2, ratio)) if ratio is not None else 1.0


async def predict_home_demand(
    home: dict[str, Any],
    target_day: date,
    weather_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    appliances = home_appliances(home["id"])
    weather = weather_data or await weather_for_home(home, target_day)
    reference_cdh, reference_hdh = await reference_degree_hours(home)
    client = get_supabase()
    log_response = (
        client.table("daily_logs")
        .select("ac_hours,outage_hours,guests,appliance_hours,log_date")
        .eq("home_id", home["id"])
        .eq("log_date", target_day.isoformat())
        .limit(1)
        .execute()
    )
    context = log_response.data[0] if log_response.data else {}
    recent = (
        client.table("daily_logs")
        .select("log_date,source")
        .eq("home_id", home["id"])
        .gte("log_date", (target_day - timedelta(days=90)).isoformat())
        .lte("log_date", target_day.isoformat())
        .execute()
    )
    n_days = sum(
        1 for row in recent.data or [] if row.get("source", "user") == "user"
    )
    model = load_model(home["id"])
    params = (model.get("params") or {}) if model else {}
    fitted = bool(
        model and int(model.get("n_days") or 0) >= MIN_DAYS_FOR_PERSONAL_FIT
    )
    prediction = predict_demand(
        appliances,
        weather["hourly"],
        cdh_reference=reference_cdh,
        hdh_reference=reference_hdh,
        context={
            **context,
            "comfort_scale": params.get("s_ac", 1.0) if fitted else 1.0,
            "fixed_scale": params.get("s_other", 1.0) if fitted else 1.0,
            "global_scale": 1.0
            if fitted
            else bill_scale(home["id"], appliances),
        },
        n_days=n_days,
        residual_std=(model.get("metrics") or {}).get("residual_std")
        if model
        else None,
    )
    return {
        "day": target_day.isoformat(),
        **prediction,
        "weather_source": weather["source"],
        "weather_stale": weather["stale"],
        "normal_city": weather["normal_city"],
        "learning_days": n_days,
    }
