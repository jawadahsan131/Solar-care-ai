from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.routers.checkin import CheckinInput
from app.main import app
from fastapi.testclient import TestClient


def test_checkin_input_accepts_today_and_bounded_values() -> None:
    payload = CheckinInput(
        date=date.today(),
        ac_hours=4.5,
        outage_hours=2,
        guests=False,
        meter_kwh=12.4,
        appliance_hours={"washing_machine": 1.5},
    )

    assert payload.ac_hours == 4.5


def test_checkin_rejects_future_dates_out_of_range_hours_and_synthetic_source() -> None:
    with pytest.raises(ValidationError):
        CheckinInput(date=date.today() + timedelta(days=1))
    with pytest.raises(ValidationError):
        CheckinInput(date=date.today(), ac_hours=25)
    with pytest.raises(ValidationError):
        CheckinInput(date=date.today(), appliance_hours={"unknown_load": 2})
    with pytest.raises(ValidationError):
        CheckinInput(date=date.today(), source="synthetic")


def test_checkin_routes_require_authentication() -> None:
    client = TestClient(app)
    assert client.get("/homes/test-home/checkins").status_code == 401
    assert client.get("/homes/test-home/demand").status_code == 401
    assert client.get("/homes/test-home/verdicts").status_code == 401
