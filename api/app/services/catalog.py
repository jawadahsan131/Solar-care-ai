import csv
import logging
import math
from pathlib import Path
from typing import Any

from rapidfuzz.fuzz import WRatio, ratio

from app.schemas import ALLOWED_TYPES

logger = logging.getLogger(__name__)

CATALOG_COLUMNS = [
    "type",
    "brand",
    "model",
    "capacity_value",
    "capacity_unit",
    "rated_watts",
    "duty_factor",
    "inverter",
    "surge_factor",
    "default_hours",
    "source",
    "verified",
    "notes",
]

def _fallback(
    appliance_type: str,
    watts: float,
    duty: float,
    surge: float,
    hours: float,
) -> dict[str, Any]:
    return {
        "type": appliance_type,
        "brand": None,
        "model": None,
        "capacity_value": None,
        "capacity_unit": None,
        "rated_watts": watts,
        "duty_factor": duty,
        "inverter": None,
        "surge_factor": surge,
        "default_hours": hours,
        "source": "typical",
        "verified": False,
        "notes": "Fallback estimate; check rating plate.",
    }


FALLBACK_ROWS = [
    {
        "type": "ac",
        "brand": None,
        "model": None,
        "capacity_value": 1.5,
        "capacity_unit": "ton",
        "rated_watts": 1700.0,
        "duty_factor": 0.65,
        "inverter": False,
        "surge_factor": 4.0,
        "default_hours": 8.0,
        "source": "typical",
        "verified": False,
        "notes": "Fallback estimate; check rating plate.",
    },
    _fallback("ceiling_fan", 75, 1.0, 1.3, 10),
    _fallback("refrigerator", 150, 0.4, 3.5, 24),
    _fallback("tv", 60, 1.0, 1.0, 5),
    _fallback("led_bulb", 12, 1.0, 1.0, 6),
    _fallback("washing_machine", 400, 1.0, 2.5, 1),
]


def load_catalog(path: str | Path) -> list[dict[str, Any]]:
    """Load appliance rows from CSV, parsing numeric and boolean fields."""
    catalog_path = Path(path)
    if not catalog_path.is_file():
        logger.warning("Appliance catalog %s is missing; using fallback rows", catalog_path)
        return [row.copy() for row in FALLBACK_ROWS]

    with catalog_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != CATALOG_COLUMNS:
            raise ValueError(
                f"Catalog columns must exactly match: {','.join(CATALOG_COLUMNS)}"
            )
        rows = []
        for line_number, source_row in enumerate(reader, start=2):
            row = {key: value.strip() if value is not None else "" for key, value in source_row.items()}
            if not row.get("type") or not row.get("rated_watts"):
                raise ValueError(f"Catalog row {line_number} is missing type or rated_watts")
            try:
                appliance_type = row["type"].lower()
                if appliance_type not in ALLOWED_TYPES:
                    raise ValueError("unsupported appliance type")
                if row["verified"].lower() not in {"true", "false"}:
                    raise ValueError("verified value must be true or false")
                parsed = {
                    "type": appliance_type,
                    "brand": _none(row["brand"]),
                    "model": _none(row["model"]),
                    "capacity_value": _float_or_none(row["capacity_value"]),
                    "capacity_unit": _none(row["capacity_unit"]),
                    "rated_watts": float(row["rated_watts"]),
                    "duty_factor": float(row["duty_factor"]),
                    "inverter": _bool_or_none(row["inverter"]),
                    "surge_factor": float(row["surge_factor"]),
                    "default_hours": _float_or_none(row["default_hours"]),
                    "source": row["source"] or "typical",
                    "verified": row["verified"].lower() == "true",
                    "notes": _none(row["notes"]),
                }
            except ValueError as exc:
                raise ValueError(f"Invalid value in catalog row {line_number}") from exc
            if parsed["rated_watts"] < 0:
                raise ValueError(f"Catalog row {line_number} has negative rated_watts")
            if not 0 < parsed["duty_factor"] <= 1 or parsed["surge_factor"] < 1:
                raise ValueError(f"Catalog row {line_number} has invalid duty/surge factor")
            if (
                parsed["default_hours"] is not None
                and not 0 <= parsed["default_hours"] <= 24
            ):
                raise ValueError(f"Catalog row {line_number} has invalid default_hours")
            rows.append(parsed)
    if not rows:
        raise ValueError("Catalog must contain at least one data row")
    return rows


def normalize_catalog_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate Supabase catalog rows and return the shared catalog shape."""
    normalized = []
    for index, row in enumerate(rows, start=1):
        appliance_type = str(row.get("type") or "").lower()
        try:
            rated_watts = float(row["rated_watts"])
            duty_factor = float(row["duty_factor"])
            surge_factor = float(row["surge_factor"])
            capacity_value = _optional_float(row.get("capacity_value"))
            default_hours = _optional_float(row.get("default_hours"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Supabase catalog values in row {index}") from exc

        if appliance_type not in ALLOWED_TYPES:
            raise ValueError(f"Unsupported appliance type in Supabase catalog row {index}")
        if not math.isfinite(rated_watts) or rated_watts < 0:
            raise ValueError(f"Invalid rated_watts in Supabase catalog row {index}")
        if not math.isfinite(duty_factor) or not 0 < duty_factor <= 1:
            raise ValueError(f"Invalid duty_factor in Supabase catalog row {index}")
        if not math.isfinite(surge_factor) or surge_factor < 1:
            raise ValueError(f"Invalid surge_factor in Supabase catalog row {index}")
        if capacity_value is not None and (
            not math.isfinite(capacity_value) or capacity_value < 0
        ):
            raise ValueError(f"Invalid capacity_value in Supabase catalog row {index}")
        if default_hours is not None and (
            not math.isfinite(default_hours) or not 0 <= default_hours <= 24
        ):
            raise ValueError(f"Invalid default_hours in Supabase catalog row {index}")

        inverter = row.get("inverter")
        verified = row.get("verified", False)
        if inverter is not None and not isinstance(inverter, bool):
            raise ValueError(f"Invalid inverter value in Supabase catalog row {index}")
        if not isinstance(verified, bool):
            raise ValueError(f"Invalid verified value in Supabase catalog row {index}")

        normalized.append(
            {
                "type": appliance_type,
                "brand": row.get("brand") or None,
                "model": row.get("model") or None,
                "capacity_value": capacity_value,
                "capacity_unit": row.get("capacity_unit") or None,
                "rated_watts": rated_watts,
                "duty_factor": duty_factor,
                "inverter": inverter,
                "surge_factor": surge_factor,
                "default_hours": default_hours,
                "source": row.get("source") or "typical",
                "verified": verified,
                "notes": row.get("notes") or None,
            }
        )
    if not normalized:
        raise ValueError("Supabase appliance catalog contains no rows")
    return normalized


def match(
    catalog: list[dict[str, Any]],
    appliance_type: str,
    brand: str | None,
    model: str | None,
    capacity_value: float | None,
    capacity_unit: str | None,
    inverter: bool | None,
) -> tuple[dict[str, Any] | None, str]:
    """Match appliance details to catalog row; return the row and match level."""
    type_rows = [
        row
        for row in catalog
        if row["type"] == appliance_type.lower() and _inverter_compatible(row, inverter)
    ]
    if not type_rows:
        return None, "none"

    if brand and model:
        requested = _normalize(f"{brand} {model}")
        exact_candidates = [
            row
            for row in type_rows
            if row["brand"]
            and row["model"]
            and ratio(requested, _normalize(f'{row["brand"]} {row["model"]}')) >= 90
        ]
        if exact_candidates:
            candidate = _best_capacity(exact_candidates, capacity_value, capacity_unit)
            return candidate, "exact"

    if brand:
        brand_candidates = [
            row for row in type_rows if row["brand"] and _normalize(row["brand"]) == _normalize(brand)
        ]
        candidate = _best_capacity(brand_candidates, capacity_value, capacity_unit)
        if candidate:
            return candidate, "brand_capacity"

    if capacity_value is not None and capacity_unit:
        capacity_candidates = [
            row
            for row in type_rows
            if _capacity_matches(row, capacity_value, capacity_unit)
        ]
        if capacity_candidates:
            return capacity_candidates[0], "type_capacity"
    if type_rows:
        return _preferred_type_row(type_rows), "type_only"
    return None, "none"


def search(
    catalog: list[dict[str, Any]],
    q: str = "",
    appliance_type: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search catalog rows using fuzzy matching over identifying fields."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    query = _normalize(q)
    filtered = [
        row
        for row in catalog
        if not appliance_type or row["type"] == appliance_type.lower()
    ]
    if not query:
        return filtered[:limit]
    return sorted(
        filtered,
        key=lambda row: _search_score(row, query),
        reverse=True,
    )[:limit]


def types_info(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one default-hours and typical-watts record for every catalog type."""
    result = []
    for appliance_type in sorted({row["type"] for row in catalog}):
        row = _preferred_type_row(
            [entry for entry in catalog if entry["type"] == appliance_type]
        )
        result.append(
            {
                "type": appliance_type,
                "default_hours": row["default_hours"],
                "typical_watts": row["rated_watts"],
            }
        )
    return result


def _preferred_type_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    type_level = [row for row in rows if not row["brand"] and not row["model"]]
    return type_level[0] if type_level else rows[0]


def _best_capacity(
    rows: list[dict[str, Any]],
    capacity_value: float | None,
    capacity_unit: str | None,
) -> dict[str, Any] | None:
    if not rows:
        return None
    matching = [
        row for row in rows if _capacity_matches(row, capacity_value, capacity_unit)
    ]
    return matching[0] if matching else (rows[0] if capacity_value is None else None)


def _capacity_matches(
    row: dict[str, Any], value: float | None, unit: str | None
) -> bool:
    row_value = row["capacity_value"]
    row_unit = row["capacity_unit"]
    if value is None or not unit or row_value is None or not row_unit:
        return value is None and row_value is None
    if unit.lower() != row_unit.lower():
        return False
    return abs(row_value - value) <= abs(value) * 0.1


def _inverter_compatible(row: dict[str, Any], inverter: bool | None) -> bool:
    return inverter is None or row["inverter"] is None or row["inverter"] == inverter


def _search_score(row: dict[str, Any], query: str) -> float:
    text = _normalize(
        " ".join(
            str(row[key] or "")
            for key in ("brand", "model", "type", "capacity_value", "capacity_unit")
        )
    )
    return float(WRatio(query, text))


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _none(value: str) -> str | None:
    return value or None


def _float_or_none(value: str) -> float | None:
    return float(value) if value else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None and value != "" else None


def _bool_or_none(value: str) -> bool | None:
    if not value:
        return None
    normalized = value.lower()
    if normalized not in {"true", "false"}:
        raise ValueError("boolean value must be true or false")
    return normalized == "true"
