from datetime import date

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.deps import get_owned_home
from app.main import app


def _set_bill_route_overrides() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "test-user",
        "email": "test@example.com",
    }
    app.dependency_overrides[get_owned_home] = lambda: {
        "id": "test-home",
        "user_id": "test-user",
    }


def test_bill_preview_accepts_manual_json_and_normalizes_month() -> None:
    current_billing_month = date.today().replace(day=15)
    _set_bill_route_overrides()
    try:
        response = TestClient(app).post(
            "/homes/test-home/bill",
            json={"month": current_billing_month.isoformat(), "units_kwh": 421.3},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["parsed"]["month"] == current_billing_month.replace(day=1).isoformat()
    assert response.json()["parsed"]["units_kwh"] == 421.3


def test_bill_preview_rejects_future_month() -> None:
    future_month = date(date.today().year + 10, 1, 1)
    _set_bill_route_overrides()
    try:
        response = TestClient(app).post(
            "/homes/test-home/bill",
            json={"month": future_month.isoformat(), "units_kwh": 10},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_bill_photo_requires_explicit_third_party_consent() -> None:
    _set_bill_route_overrides()
    try:
        response = TestClient(app).post(
            "/homes/test-home/bill",
            files={"image": ("bill.jpg", b"not-read-before-consent", "image/jpeg")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "Confirm" in response.json()["error"]
