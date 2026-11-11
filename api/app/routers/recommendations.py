from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.db import get_supabase
from app.deps import AuthenticatedUser, OwnedHome
from app.services.home_demand import predict_home_demand
from app.services.recommend import optimize_plan
from app.services.solar import daily_summary, pv_curve
from app.services.tariff import estimate_import_saving
from app.services.weather import get_weather_days

router = APIRouter(prefix="/homes", tags=["recommendations"])
LOCAL_TZ = ZoneInfo("Asia/Karachi")


class RecommendationFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date
    status: Literal["done", "skipped", "not_possible"]


def _blocked_windows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows = []
    for row in rows:
        parts = str(row.get("rec_id") or "").split("@")
        if row.get("status") != "not_possible" or len(parts) != 3:
            continue
        try:
            destination_hours = [int(value) for value in parts[2].split(",") if value]
        except ValueError:
            continue
        windows.append({"item_id": parts[0], "hours": destination_hours})
    return windows


@router.get("/{home_id}/recommendations")
async def get_recommendations(
    home: OwnedHome,
    user: AuthenticatedUser,
    day: date | None = Query(default=None, alias="date"),
    panel_kw: float | None = Query(default=None, ge=0, le=100),
    battery_kwh: float | None = Query(default=None, ge=0, le=200),
) -> dict[str, Any]:
    if home.get("lat") is None or home.get("lon") is None:
        raise HTTPException(
            status_code=400,
            detail="Set your city in the forecast page before viewing solar recommendations.",
        )
    target_day = day or datetime.now(LOCAL_TZ).date()
    system_kw = float(home.get("system_kw") or panel_kw or 0.0)
    if panel_kw is not None:
        system_kw = panel_kw
    try:
        weather = (await get_weather_days(
            float(home["lat"]),
            float(home["lon"]),
            [target_day],
            str(home.get("city") or ""),
        ))[0]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    demand = await predict_home_demand(home, target_day, weather_data=weather)
    response = (
        get_supabase()
        .table("home_appliances")
        .select("*")
        .eq("home_id", home["id"])
        .execute()
    )
    appliances = response.data or []
    solar_kw = [
        value * system_kw
        for value in pv_curve(
            weather["hourly"]["ghi_wm2"], weather["hourly"]["temp_c"]
        )
    ]
    feedback_response = (
        get_supabase()
        .table("recommendation_feedback")
        .select("rec_id,status")
        .eq("home_id", home["id"])
        .eq("status", "not_possible")
        .gte("created_at", (datetime.now(LOCAL_TZ) - timedelta(days=30)).isoformat())
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    optimization = optimize_plan(
        solar_kw,
        demand["hourly_kw"],
        appliances,
        blocked_windows=_blocked_windows(feedback_response.data or []),
        battery_kwh=battery_kwh,
        mean_cloud_pct=sum(weather["hourly"]["cloud_pct"]) / 24,
        unserved_kwh=demand.get("unserved_kwh", 0.0),
    )
    cost = estimate_import_saving(
        optimization["metrics"]["grid_import_kwh"],
        optimization["metrics"]["plan_grid_import_kwh"],
    )
    return {
        "day": target_day.isoformat(),
        "summary": daily_summary(weather["hourly"])["text"],
        "system_kw": system_kw,
        "weather_source": weather["source"],
        "weather_stale": weather["stale"],
        "metrics": {**optimization["metrics"], **cost},
        "solar_kw": [round(value, 3) for value in solar_kw],
        "load_kw": demand["hourly_kw"],
        "plan_load_kw": optimization["plan_load_kw"],
        "recommendations": optimization["recommendations"],
        "tips": optimization["tips"],
    }


@router.post("/{home_id}/recommendations/{rec_id}/feedback")
def save_recommendation_feedback(
    home: OwnedHome,
    user: AuthenticatedUser,
    rec_id: str,
    payload: RecommendationFeedback,
) -> dict[str, Any]:
    response = (
        get_supabase()
        .table("recommendation_feedback")
        .insert(
            {
                "home_id": home["id"],
                "day": payload.day.isoformat(),
                "rec_id": rec_id,
                "status": payload.status,
            }
        )
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Recommendation feedback could not be saved")
    return response.data[0]
