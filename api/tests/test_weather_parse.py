import json
from datetime import date
from pathlib import Path

import pytest

from app.services.weather import parse_open_meteo, rounded_coordinates

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "open_meteo_sample.json"


def test_open_meteo_fixture_parses_local_hourly_values() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    parsed = parse_open_meteo(payload)

    assert list(parsed) == ["2026-11-11"]
    assert len(parsed["2026-11-11"]["temp_c"]) == 24
    assert parsed["2026-11-11"]["temp_c"][13] == pytest.approx(28.1)
    assert parsed["2026-11-11"]["ghi_wm2"][12] == pytest.approx(550)


def test_weather_series_interpolates_short_gaps_and_skips_long_gaps() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["hourly"]["temperature_2m"][9:11] = [None, None]
    parsed = parse_open_meteo(payload)
    assert parsed["2026-11-11"]["temp_c"][9] == pytest.approx(
        19.9 + (26.1 - 19.9) / 3
    )

    payload["hourly"]["temperature_2m"][5:10] = [None] * 5
    assert parse_open_meteo(payload) == {}


def test_weather_cache_coordinates_are_rounded_to_two_decimals() -> None:
    assert rounded_coordinates(31.52041, 74.35871) == (31.52, 74.36)


def test_weather_fixture_has_requested_day() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert date.fromisoformat(parse_open_meteo(payload).popitem()[0]) == date(2026, 11, 11)
