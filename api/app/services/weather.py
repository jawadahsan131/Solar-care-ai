from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from starlette.concurrency import run_in_threadpool

from app.db import get_supabase
from app.services.cities import PAKISTANI_CITIES
from app.services.part2_config import WEATHER_CACHE_TTL_SECONDS, WEATHER_TIMEOUT_SECONDS

logger = logging.getLogger("solar_care.weather")
WEATHER_VARIABLES = (
    "temperature_2m,relative_humidity_2m,cloud_cover,shortwave_radiation"
)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
NORMALS_PATH = Path(__file__).parents[3] / "data" / "climate_normals.json"
LOCAL_TZ = ZoneInfo("Asia/Karachi")
_weather_normals: dict[str, Any] | None = None


def rounded_coordinates(lat: float, lon: float) -> tuple[float, float]:
    return round(float(lat), 2), round(float(lon), 2)


def _interpolate(values: list[float | None]) -> list[float]:
    valid = [index for index, value in enumerate(values) if value is not None]
    if not valid:
        raise ValueError("Weather series contains no usable values")
    result = list(values)
    for index, value in enumerate(result):
        if value is not None:
            continue
        left = max((candidate for candidate in valid if candidate < index), default=None)
        right = min((candidate for candidate in valid if candidate > index), default=None)
        if left is None or right is None:
            nearest = right if left is None else left
            assert nearest is not None
            if abs(nearest - index) > 3:
                raise ValueError("Weather data has a gap longer than 3 hours")
            result[index] = result[nearest]
            continue
        gap = right - left - 1
        if gap > 3:
            raise ValueError("Weather data has a gap longer than 3 hours")
        left_value = result[left]
        right_value = result[right]
        assert left_value is not None and right_value is not None
        result[index] = left_value + (right_value - left_value) * (
            (index - left) / (right - left)
        )
    return [float(value) for value in result if value is not None]


def parse_open_meteo(payload: dict[str, Any]) -> dict[str, dict[str, list[float]]]:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        raise ValueError("Open-Meteo response is missing hourly values")
    fields = {
        "temp_c": "temperature_2m",
        "humidity_pct": "relative_humidity_2m",
        "cloud_pct": "cloud_cover",
        "ghi_wm2": "shortwave_radiation",
    }
    times = hourly["time"]
    if any(not isinstance(hourly.get(name), list) or len(hourly[name]) != len(times) for name in fields.values()):
        raise ValueError("Open-Meteo response has incomplete hourly arrays")
    days: dict[str, dict[str, list[float | None]]] = {}
    for field in fields:
        days[field] = {}
    for index, raw_time in enumerate(times):
        try:
            timestamp = datetime.fromisoformat(raw_time)
        except (TypeError, ValueError):
            continue
        day_key = timestamp.date().isoformat()
        if day_key not in days["temp_c"]:
            for field in fields:
                days[field][day_key] = [None] * 24
        hour = timestamp.hour
        for field, raw_name in fields.items():
            raw_value = hourly[raw_name][index]
            if raw_value is None:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            days[field][day_key][hour] = value

    parsed: dict[str, dict[str, list[float]]] = {}
    for day_key in days["temp_c"]:
        try:
            row = {
                field: _interpolate(days[field][day_key])
                for field in fields
            }
        except ValueError:
            continue
        if any(not 0 <= value <= 100 for value in row["humidity_pct"]):
            continue
        if any(not 0 <= value <= 100 for value in row["cloud_pct"]):
            continue
        if any(value < 0 for value in row["ghi_wm2"]):
            continue
        parsed[day_key] = row
    return parsed


async def _fetch_open_meteo(
    kind: str, lat: float, lon: float, start_day: date, end_day: date
) -> dict[str, dict[str, list[float]]]:
    endpoint = FORECAST_URL if kind == "forecast" else ARCHIVE_URL
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": WEATHER_VARIABLES,
        "timezone": "Asia/Karachi",
        "start_date": start_day.isoformat(),
        "end_date": end_day.isoformat(),
    }
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=WEATHER_TIMEOUT_SECONDS) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
            return parse_open_meteo(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                continue
    raise RuntimeError(f"Open-Meteo {kind} request failed after retry") from last_error


def _cache_rows(lat2: float, lon2: float, day_keys: list[str]) -> dict[str, dict[str, Any]]:
    if not day_keys:
        return {}
    response = (
        get_supabase()
        .table("weather_cache")
        .select("day,kind,hourly,fetched_at")
        .eq("lat2", lat2)
        .eq("lon2", lon2)
        .in_("day", day_keys)
        .execute()
    )
    return {str(row["day"]): row for row in response.data or []}


def _save_cache_rows(
    lat2: float,
    lon2: float,
    rows: list[dict[str, Any]],
) -> None:
    if rows:
        get_supabase().table("weather_cache").upsert(
            [
                {
                    "lat2": lat2,
                    "lon2": lon2,
                    "day": row["day"],
                    "kind": row["kind"],
                    "hourly": row["hourly"],
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                for row in rows
            ],
            on_conflict="lat2,lon2,day,kind",
        ).execute()


def _cache_is_fresh(row: dict[str, Any], kind: str) -> bool:
    if kind == "archive":
        return True
    try:
        fetched_at = datetime.fromisoformat(
            str(row["fetched_at"]).replace("Z", "+00:00")
        )
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return False
    return (datetime.now(timezone.utc) - fetched_at).total_seconds() < WEATHER_CACHE_TTL_SECONDS


def _load_normals() -> dict[str, Any]:
    global _weather_normals
    if _weather_normals is None:
        with NORMALS_PATH.open(encoding="utf-8") as file:
            _weather_normals = json.load(file)
    return _weather_normals


def _normal_city(lat: float, lon: float, city: str | None) -> dict[str, Any]:
    normals = _load_normals()["cities"]
    if city:
        for entry in PAKISTANI_CITIES:
            if entry["name"].casefold() == city.casefold():
                return normals[entry["name"]]
    nearest = min(
        PAKISTANI_CITIES,
        key=lambda item: (item["lat"] - lat) ** 2 + (item["lon"] - lon) ** 2,
    )
    return normals[nearest["name"]]


def climate_normal(lat: float, lon: float, day: date, city: str | None) -> tuple[dict[str, list[float]], str]:
    normal = _normal_city(lat, lon, city)
    month = normal["months"][str(day.month)]
    daylight_hours = 12 + 4.2 * math.cos(2 * math.pi * (day.month - 6.5) / 12)
    sunrise = 12 - daylight_hours / 2
    solar_weights = [
        max(0.0, math.sin(math.pi * ((hour + 0.5 - sunrise) / daylight_hours)))
        for hour in range(24)
    ]
    total_weight = sum(solar_weights) or 1
    target_wh = float(month["daily_ghi_kwh_m2"]) * 1000
    ghi = [weight * target_wh / total_weight for weight in solar_weights]
    temp_mean = float(month["temp_mean_c"])
    temperatures = [
        temp_mean + 6 * math.cos(2 * math.pi * (hour - 15) / 24)
        for hour in range(24)
    ]
    return (
        {
            "temp_c": [round(value, 2) for value in temperatures],
            "humidity_pct": [float(month["humidity_pct"])] * 24,
            "cloud_pct": [float(month["cloud_pct"])] * 24,
            "ghi_wm2": [round(value, 2) for value in ghi],
        },
        normal["name"],
    )


async def get_weather_days(
    lat: float,
    lon: float,
    requested_days: list[date],
    city: str | None = None,
) -> list[dict[str, Any]]:
    if not requested_days:
        return []
    today = datetime.now(LOCAL_TZ).date()
    if any(day > today + timedelta(days=7) for day in requested_days):
        raise ValueError("Weather forecast is available up to 7 days ahead")
    lat2, lon2 = rounded_coordinates(lat, lon)
    day_keys = [day.isoformat() for day in requested_days]
    try:
        cached = await run_in_threadpool(_cache_rows, lat2, lon2, day_keys)
    except Exception:
        logger.exception("Could not read weather cache")
        cached = {}

    results: dict[str, dict[str, Any]] = {}
    fetch_by_kind: dict[str, list[date]] = {"forecast": [], "archive": []}
    for day in requested_days:
        kind = "archive" if day < today else "forecast"
        row = cached.get(day.isoformat())
        if row and row.get("kind") == kind and _cache_is_fresh(row, kind):
            results[day.isoformat()] = {
                "hourly": row["hourly"],
                "source": kind,
                "stale": False,
                "normal_city": None,
            }
        else:
            fetch_by_kind[kind].append(day)

    cache_to_save: list[dict[str, Any]] = []
    for kind, days in fetch_by_kind.items():
        if not days:
            continue
        try:
            fetched = await _fetch_open_meteo(kind, lat, lon, min(days), max(days))
            for day in days:
                day_key = day.isoformat()
                hourly = fetched.get(day_key)
                if hourly is None:
                    continue
                results[day_key] = {
                    "hourly": hourly,
                    "source": kind,
                    "stale": False,
                    "normal_city": None,
                }
                cache_to_save.append(
                    {"day": day_key, "kind": kind, "hourly": hourly}
                )
        except Exception:
            logger.exception(
                "Could not fetch Open-Meteo data for kind=%s start=%s end=%s",
                kind,
                min(days),
                max(days),
            )

    if cache_to_save:
        try:
            await run_in_threadpool(
                _save_cache_rows, lat2, lon2, cache_to_save
            )
        except Exception:
            logger.exception("Could not write weather cache")

    output = []
    for day in requested_days:
        key = day.isoformat()
        if key not in results:
            cached_row = cached.get(key)
            if cached_row:
                results[key] = {
                    "hourly": cached_row["hourly"],
                    "source": cached_row.get("kind", "archive"),
                    "stale": True,
                    "normal_city": None,
                }
            else:
                normal, normal_city = climate_normal(lat, lon, day, city)
                results[key] = {
                    "hourly": normal,
                    "source": "normal",
                    "stale": False,
                    "normal_city": normal_city,
                }
        output.append({"day": key, **results[key]})
    return output
