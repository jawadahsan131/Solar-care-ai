from fastapi.testclient import TestClient

from app.main import app
from app.services.appliances import (
    build_load_items,
    configured_catalog_path,
    prepare_appliance_data,
)
from app.services.catalog import load_catalog
from app.schemas import HomeOut

client = TestClient(app)
CATALOG = load_catalog(configured_catalog_path())


def test_create_payload_always_has_24_hour_schedule() -> None:
    row = prepare_appliance_data(
        {
            "type": "ac",
            "watts": 1200,
            "hourly_use": [],
            "hours_per_day": 2.5,
        },
        "home-id",
        CATALOG,
    )
    assert len(row["hourly_use"]) == 24
    assert sum(row["hourly_use"]) == 2.5


def test_load_items_preserve_saved_schedule() -> None:
    schedule = [1.0] + [0.0] * 23
    items = build_load_items(
        [
            {
                "type": "refrigerator",
                "qty": 2,
                "watts": 150,
                "duty_factor": 0.4,
                "surge_factor": 3,
                "hourly_use": schedule,
                "is_essential": True,
            }
        ],
        CATALOG,
    )
    assert items[0].hourly_use == schedule
    assert items[0].qty == 2
    assert items[0].is_essential


def test_health_endpoint_is_public() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_authenticated_routes_reject_missing_access_token() -> None:
    response = client.get("/homes")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_home_response_accepts_all_database_columns() -> None:
    home = HomeOut.model_validate(
        {
            "id": "home-id",
            "user_id": "user-id",
            "name": "Demo home",
            "city": "Lahore",
            "lat": None,
            "lon": None,
            "family_size": 5,
            "system_kw": None,
            "created_at": "2026-11-03T08:30:00Z",
            "appliance_count": 0,
        }
    )
    assert home.system_kw is None


def test_configured_catalog_path_is_independent_of_working_directory(monkeypatch, tmp_path) -> None:
    from app.config import settings

    monkeypatch.setattr(
        settings,
        "catalog_path",
        "../data/catalog/appliance_catalog.csv",
    )
    monkeypatch.chdir(tmp_path)
    catalog_path = configured_catalog_path()

    assert catalog_path.is_file()
    assert catalog_path.name == "appliance_catalog.csv"
