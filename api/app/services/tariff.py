from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("solar_care.tariff")
TARIFF_PATH = Path(__file__).parents[3] / "data" / "tariff.json"


def load_tariff(path: Path = TARIFF_PATH) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read the editable tariff file")
        return None
    if not isinstance(data, dict):
        return None
    slabs = data.get("slabs")
    if not isinstance(slabs, list) or not slabs or any(not isinstance(slab, dict) for slab in slabs):
        return None
    previous_limit = 0.0
    for slab in slabs:
        limit = slab.get("up_to_kwh")
        rate = slab.get("rate_pkr_per_kwh")
        if (
            not isinstance(limit, (int, float))
            or not isinstance(rate, (int, float))
            or limit <= previous_limit
            or rate < 0
        ):
            return None
        previous_limit = float(limit)
    if not isinstance(data.get("tax_percent"), (int, float)) or data["tax_percent"] < 0:
        return None
    for field in ("fuel_adjustment_pkr_per_kwh", "other_charges_percent"):
        value = data.get(field)
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            return None
    return data


def estimated_import_cost(import_kwh: float, tariff: dict[str, Any]) -> float:
    remaining = max(0.0, float(import_kwh))
    previous_limit = 0.0
    energy_cost = 0.0
    slabs = tariff["slabs"]
    for index, slab in enumerate(slabs):
        limit = float(slab["up_to_kwh"])
        slab_size = max(0.0, limit - previous_limit)
        if index == len(slabs) - 1:
            slab_size = remaining
        used = min(remaining, slab_size)
        energy_cost += used * float(slab["rate_pkr_per_kwh"])
        remaining -= used
        previous_limit = limit
        if remaining <= 0:
            break
    if remaining > 0:
        energy_cost += remaining * float(slabs[-1]["rate_pkr_per_kwh"])
    fuel = float(tariff.get("fuel_adjustment_pkr_per_kwh") or 0) * max(0.0, float(import_kwh))
    other_pct = float(tariff.get("other_charges_percent") or 0) / 100
    tax_pct = float(tariff.get("tax_percent") or 0) / 100
    subtotal = energy_cost + fuel
    return round(subtotal * (1 + other_pct) * (1 + tax_pct), 2)


def estimate_import_saving(
    before_kwh: float, after_kwh: float
) -> dict[str, Any]:
    tariff = load_tariff()
    if tariff is None:
        return {
            "estimated_saving_pkr": None,
            "cost_label": "Tariff estimate unavailable; update data/tariff.json to enable cost estimates.",
            "tariff_updated_on": None,
        }
    before = estimated_import_cost(before_kwh, tariff)
    after = estimated_import_cost(after_kwh, tariff)
    return {
        "estimated_saving_pkr": round(max(0.0, before - after), 2),
        "cost_label": f"Estimate only; tariff updated on {tariff.get('updated_on', 'unknown date')}.",
        "tariff_updated_on": tariff.get("updated_on"),
    }
