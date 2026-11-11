from __future__ import annotations

from statistics import median
from typing import Any

from app.services.schedules import default_hourly_use

COMFORT_TYPES = {"ac", "air_cooler", "ceiling_fan", "pedestal_fan"}
FLEXIBLE_TYPES = {
    "washing_machine",
    "iron",
    "water_pump",
    "geyser",
    "vacuum_cleaner",
    "electric_oven",
    "ups",
    "water_dispenser",
}
PROTECTED_TYPES = {"refrigerator", "deep_freezer", "router", "led_bulb", "tube_light", "tv"}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        item = item.model_dump()
    if not isinstance(item, dict):
        raise TypeError("Each appliance item must be a dict-like object")
    return item


def _hourly_use_for(item: dict[str, Any]) -> list[float]:
    item = _normalize_item(item)
    hourly_use = item.get("hourly_use")
    if isinstance(hourly_use, list) and len(hourly_use) == 24:
        return [float(value) for value in hourly_use]

    hours_per_day = item.get("hours_per_day")
    if hours_per_day is None:
        hours_per_day = item.get("default_hours", 2.0)
    type_name = str(item.get("type") or "other")
    return default_hourly_use(type_name, float(hours_per_day))


def estimate_daily_kwh(item: dict[str, Any]) -> float:
    item = _normalize_item(item)
    qty = max(1, int(item.get("qty", item.get("count", 1))))
    watts = max(0.0, _as_float(item.get("watts"), 0.0))
    duty = max(0.0, _as_float(item.get("duty_factor", 1.0), 1.0))
    hourly_use = _hourly_use_for(item)
    return qty * watts / 1000 * duty * sum(hourly_use)


def estimate_monthly_kwh(items: list[dict[str, Any]], month_factor: float = 1.0) -> float:
    """Return estimated monthly kWh for a home item list, applying a seasonal factor."""
    factor = max(0.0, _as_float(month_factor, 1.0))
    daily_kwh = sum(estimate_daily_kwh(item) for item in items)
    return round(daily_kwh * 30.0 * factor, 2)


def calibration_ratio(bill_units: float, estimated_units: float) -> float:
    """Return bill / estimate. A value of 1.0 means the estimate matches the bill."""
    bill = _as_float(bill_units, 0.0)
    estimate = _as_float(estimated_units, 0.0)
    if estimate <= 0:
        if bill <= 0:
            return 1.0
        return float("inf")
    return bill / estimate


def calibration_verdict(ratio: float) -> dict[str, Any]:
    """Map the calibration ratio to a human-friendly verdict and likely reasons."""
    ratio = _as_float(ratio, 1.0)
    delta_pct = abs(ratio - 1.0) * 100.0
    if delta_pct <= 15.0 + 1e-9:
        band = "good match"
    elif delta_pct <= 30.0 + 1e-9:
        band = "check hours/quantities"
    else:
        band = "estimate is far from your bill"

    reasons: list[str] = []
    if ratio > 1.3:
        reasons.extend([
            "missed appliances",
            "hours too low",
        ])
    elif ratio < 0.7:
        reasons.extend([
            "hours too high",
            "quantities are overestimated",
        ])
    else:
        reasons.append("usage is close enough for a quick review")

    if ratio > 1.0:
        reasons.append("AC usage differences")
    reasons.append("the bill is units-only and may include other charges")
    return {
        "ratio": ratio,
        "percentage_delta": round(delta_pct, 2),
        "band": band,
        "reasons": sorted(set(reasons), key=reasons.index),
    }


def overall_calibration_ratio(history: list[float], estimated_units: float) -> float | None:
    """Compute a robust overall ratio from recent bills, using the median of the last 3."""
    valid = [float(value) for value in history if value is not None and value > 0]
    if not valid:
        return None
    if len(valid) > 3:
        valid = valid[-3:]
    ratios = [calibration_ratio(value, estimated_units) for value in valid]
    return float(median(ratios))


def suggest_scaling(items: list[dict[str, Any]], ratio: float) -> list[dict[str, Any]]:
    """Return simple, safe scaling proposals that do not touch protected or fixed loads."""
    if not items:
        return []

    proposals: list[dict[str, Any]] = []
    if ratio <= 1.0:
        return proposals

    candidates = []
    for item in items:
        item = _normalize_item(item)
        type_name = str(item.get("type") or "other")
        if type_name in PROTECTED_TYPES:
            continue
        if type_name in COMFORT_TYPES or type_name in FLEXIBLE_TYPES:
            candidates.append(item)

    if not candidates:
        return proposals

    scale_factor = min(max(ratio, 1.05), 1.6)
    for item in candidates:
        type_name = str(item.get("type") or "other")
        current_hours = float(item.get("hours_per_day") or sum(_hourly_use_for(item)) or 2.0)
        proposed_hours = round(max(0.0, current_hours * scale_factor), 2)
        proposals.append(
            {
                "appliance_id": item.get("id"),
                "type": type_name,
                "field": "hours_per_day",
                "current": round(current_hours, 2),
                "suggested": proposed_hours,
                "reason": "Scale weather-driven or flexible loads to match seasonal demand.",
            }
        )

    return proposals[:4]


def monthly_index(history: list[float]) -> float | None:
    """Return a relative monthly index for weather modeling when six or more months exist."""
    valid = [float(value) for value in history if value is not None and value > 0]
    if len(valid) < 6:
        return None
    average = sum(valid) / len(valid)
    if average <= 0:
        return None
    return round((valid[-1] / average), 3)
