from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.db import get_supabase
from app.services.catalog import normalize_catalog_rows
from app.services.schedules import default_hourly_use
from app.services.sizing import LoadItem


CATALOG_FIELDS = (
    "type,brand,model,capacity_value,capacity_unit,rated_watts,duty_factor,"
    "inverter,surge_factor,default_hours,source,verified,notes"
)


def configured_catalog_path() -> Path:
    path = Path(settings.catalog_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path


@lru_cache
def get_catalog() -> list[dict[str, Any]]:
    response = (
        get_supabase()
        .table("appliance_catalog")
        .select(CATALOG_FIELDS)
        .order("type")
        .order("capacity_value")
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=503,
            detail=(
                "The Supabase appliance catalog is empty. From the api folder, "
                "run `python ..\\scripts\\seed_catalog.py` to load the catalog."
            ),
        )
    return normalize_catalog_rows(response.data)


def default_hours_for(appliance_type: str, catalog: list[dict[str, Any]]) -> float:
    type_rows = [row for row in catalog if row["type"] == appliance_type]
    if not type_rows:
        return 2.0
    preferred = next(
        (row for row in type_rows if not row.get("brand") and not row.get("model")),
        type_rows[0],
    )
    return float(preferred.get("default_hours") or 2.0)


def prepare_appliance_data(
    payload: dict[str, Any],
    home_id: str,
    catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    """Make a database-ready row and ensure it has a valid 24-hour schedule."""
    data = dict(payload)
    hours_per_day = data.pop("hours_per_day", None)
    hourly_use = data.get("hourly_use") or []
    if len(hourly_use) != 24:
        hours = (
            float(hours_per_day)
            if hours_per_day is not None
            else default_hours_for(data["type"], catalog)
        )
        hourly_use = default_hourly_use(data["type"], hours)
    data["hourly_use"] = hourly_use
    data["home_id"] = home_id
    return data


def appliance_output(row: dict[str, Any]) -> dict[str, Any]:
    """Add the UI convenience value derived from the stored hourly schedule."""
    hourly_use = row.get("hourly_use") or []
    if len(hourly_use) != 24:
        hourly_use = default_hourly_use(row["type"], 2)
    return {**row, "hourly_use": hourly_use, "hours_per_day": sum(hourly_use)}


def build_load_items(
    rows: list[dict[str, Any]], catalog: list[dict[str, Any]]
) -> list[LoadItem]:
    """Convert saved appliance rows into sizing inputs with schedule fallbacks."""
    items = []
    for row in rows:
        hourly_use = row.get("hourly_use") or []
        if len(hourly_use) != 24:
            hours = default_hours_for(row["type"], catalog)
            hourly_use = default_hourly_use(row["type"], hours)
        items.append(
            LoadItem(
                type=row["type"],
                qty=row.get("qty", 1),
                watts=row["watts"],
                duty_factor=row.get("duty_factor", 1),
                surge_factor=row.get("surge_factor", 1),
                hourly_use=hourly_use,
                is_essential=row.get("is_essential", False),
            )
        )
    return items
