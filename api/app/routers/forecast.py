from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query

from app.deps import OwnedHome
from app.services.cities import PAKISTANI_CITIES
from app.services.solar import cdh, daily_summary, pv_curve, sun_hours
from app.services.weather import get_weather_days

router = APIRouter(tags=["forecast"])
LOCAL_TZ = ZoneInfo("Asia/Karachi")


@router.get("/cities")
def list_cities() -> list[dict[str, Any]]:
    return PAKISTANI_CITIES


@router.get("/homes/{home_id}/forecast")
async def forecast_home(
    home: OwnedHome,
    start_day: date | None = Query(default=None, alias="date"),
    days: int = Query(default=1, ge=1, le=7),
) -> list[dict[str, Any]]:
    lat = home.get("lat")
    lon = home.get("lon")
    if lat is None or lon is None:
        raise HTTPException(
            status_code=400,
            detail="Set your city in the forecast page before requesting weather.",
        )
    first_day = start_day or datetime.now(LOCAL_TZ).date()
    requested_days = [first_day + timedelta(days=offset) for offset in range(days)]
    try:
        weather_days = await get_weather_days(
            float(lat),
            float(lon),
            requested_days,
            str(home.get("city") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    forecasts = []
    for weather in weather_days:
        hourly = weather["hourly"]
        summary = daily_summary(hourly)
        forecasts.append(
            {
                "day": weather["day"],
                "source": weather["source"],
                "stale": weather["stale"],
                "normal_city": weather["normal_city"],
                "hourly": hourly,
                "pv_kw_per_kwp": pv_curve(hourly["ghi_wm2"], hourly["temp_c"]),
                "sun_hours": sun_hours(hourly["ghi_wm2"]),
                "cdh": cdh(hourly["temp_c"]),
                "summary": summary["text"],
                "summary_details": summary,
                "assumptions": [
                    "PV output uses a 0.75 performance ratio and an approximate 3% soiling loss."
                ],
            }
        )
    return forecasts
