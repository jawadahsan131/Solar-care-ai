from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.deps import get_owned_home
from app.main import app


def test_cities_endpoint_lists_supported_locations() -> None:
    response = TestClient(app).get("/cities")

    assert response.status_code == 200
    assert {city["name"] for city in response.json()} >= {"Karachi", "Lahore", "Islamabad"}


def test_forecast_requires_home_coordinates() -> None:
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
        response = TestClient(app).get("/homes/test-home/forecast")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "city" in response.json()["error"]
