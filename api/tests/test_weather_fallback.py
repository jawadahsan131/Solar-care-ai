import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.services import weather


def test_weather_falls_back_to_labelled_climate_normal(monkeypatch) -> None:
    async def fail_fetch(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(weather, "_cache_rows", lambda *args: {})
    monkeypatch.setattr(weather, "_fetch_open_meteo", fail_fetch)
    target_day = datetime.now(weather.LOCAL_TZ).date()

    result = asyncio.run(
        weather.get_weather_days(31.52, 74.36, [target_day], "Lahore")
    )

    assert result[0]["source"] == "normal"
    assert result[0]["normal_city"] == "Lahore"
    assert len(result[0]["hourly"]["temp_c"]) == 24
    assert len(result[0]["hourly"]["ghi_wm2"]) == 24


def test_weather_uses_stale_cache_when_refresh_fails(monkeypatch) -> None:
    async def fail_fetch(*args, **kwargs):
        raise RuntimeError("offline")

    target_day = datetime.now(weather.LOCAL_TZ).date()
    stale_row = {
        "kind": "forecast",
        "hourly": {
            "temp_c": [25.0] * 24,
            "humidity_pct": [50.0] * 24,
            "cloud_pct": [10.0] * 24,
            "ghi_wm2": [0.0] * 24,
        },
        "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
    }
    monkeypatch.setattr(weather, "_cache_rows", lambda *args: {target_day.isoformat(): stale_row})
    monkeypatch.setattr(weather, "_fetch_open_meteo", fail_fetch)

    result = asyncio.run(
        weather.get_weather_days(31.52, 74.36, [target_day], "Lahore")
    )

    assert result[0]["source"] == "forecast"
    assert result[0]["stale"] is True
    assert result[0]["hourly"] == stale_row["hourly"]


def test_weather_rejects_gaps_larger_than_three_hours() -> None:
    assert weather._interpolate([1.0, None, None, 4.0] + [4.0] * 20)[1] == pytest.approx(2.0)
    with pytest.raises(ValueError):
        weather._interpolate([1.0, None, None, None, None, 6.0] + [6.0] * 18)


def test_repeated_fresh_cache_reads_do_not_call_open_meteo(monkeypatch) -> None:
    target_day = datetime.now(weather.LOCAL_TZ).date()
    kind = "archive" if target_day < datetime.now(weather.LOCAL_TZ).date() else "forecast"
    cached_row = {
        "kind": kind,
        "hourly": {
            "temp_c": [25.0] * 24,
            "humidity_pct": [50.0] * 24,
            "cloud_pct": [10.0] * 24,
            "ghi_wm2": [0.0] * 24,
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    upstream_calls = 0

    async def count_fetch(*args, **kwargs):
        nonlocal upstream_calls
        upstream_calls += 1
        return {}

    monkeypatch.setattr(weather, "_cache_rows", lambda *args: {target_day.isoformat(): cached_row})
    monkeypatch.setattr(weather, "_fetch_open_meteo", count_fetch)

    async def repeat_reads():
        for _ in range(100):
            await weather.get_weather_days(31.52, 74.36, [target_day], "Lahore")

    asyncio.run(repeat_reads())

    assert upstream_calls == 0
