from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.deps import get_owned_home
from app.main import app
from app.routers import whatif


def test_whatif_requires_authentication() -> None:
    response = TestClient(app).post(
        "/homes/test-home/whatif",
        json={"panel_kw": 5},
    )

    assert response.status_code == 401


def test_whatif_requires_a_saved_city() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "test-user",
        "email": "test@example.com",
    }
    app.dependency_overrides[get_owned_home] = lambda: {
        "id": "test-home",
        "user_id": "test-user",
        "lat": None,
        "lon": None,
        "city": None,
    }
    try:
        response = TestClient(app).post(
            "/homes/test-home/whatif",
            json={"panel_kw": 5},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "city" in response.json()["error"]


def test_whatif_endpoint_returns_three_zero_panel_scenarios(monkeypatch) -> None:
    class Query:
        def table(self, name):
            return self

        def select(self, fields):
            return self

        def eq(self, field, value):
            return self

        def execute(self):
            return type("Response", (), {"data": []})()

    def climate_normal(lat, lon, day, city):
        return (
            {
                "temp_c": [25.0] * 24,
                "humidity_pct": [50.0] * 24,
                "cloud_pct": [20.0] * 24,
                "ghi_wm2": [0.0] * 24,
            },
            "Test City",
        )

    monkeypatch.setattr(whatif, "get_supabase", lambda: Query())
    monkeypatch.setattr(whatif, "climate_normal", climate_normal)
    monkeypatch.setattr(whatif, "load_tariff", lambda: None)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "test-user",
        "email": "test@example.com",
    }
    app.dependency_overrides[get_owned_home] = lambda: {
        "id": "test-home",
        "user_id": "test-user",
        "lat": 24.86,
        "lon": 67.01,
        "city": "Test City",
    }
    try:
        response = TestClient(app).post(
            "/homes/test-home/whatif",
            json={"panel_kw": 0},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    assert len(result["scenarios"]) == 3
    assert all(
        scenario["sensitivity"]["base"]["yearly_solar_kwh"] == 0
        for scenario in result["scenarios"]
    )
