from __future__ import annotations

import math
from collections import defaultdict
from statistics import median
from typing import Any

from app.services.part2_config import (
    COMFORT_SETPOINT_C,
    DEMAND_FACTOR_MAX,
    DEMAND_FACTOR_MIN,
    FAN_MIN_FACTOR,
    RIDGE_LAMBDA,
)
from app.services.schedules import default_hourly_use

COMFORT_TYPES = {"ac", "air_cooler", "ceiling_fan", "pedestal_fan"}
FAN_TYPES = {"ceiling_fan", "pedestal_fan"}
AC_TYPES = {"ac", "air_cooler"}
LIGHT_TV_TYPES = {"led_bulb", "tube_light", "tv"}


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _schedule(item: dict[str, Any]) -> list[float]:
    schedule = item.get("hourly_use")
    if isinstance(schedule, list) and len(schedule) == 24:
        return [_clamp(float(value), 0.0, 1.0) for value in schedule]
    return default_hourly_use(
        str(item.get("type") or "other"),
        float(item.get("hours_per_day") or item.get("default_hours") or 2),
    )


def _shape_to_hours(shape: list[float], hours: float) -> list[float]:
    total = sum(shape)
    if total <= 0 or hours <= 0:
        return [0.0] * 24
    return [value * hours / total for value in shape]


def _degree_hours(weather: dict[str, Any], setpoint: float, heating: bool = False) -> float:
    temperatures = weather["temp_c"]
    if len(temperatures) != 24:
        raise ValueError("Temperature series must contain 24 hourly values")
    if heating:
        return sum(max(0.0, setpoint - float(value)) for value in temperatures)
    return sum(max(0.0, float(value) - setpoint) for value in temperatures)


def demand_components(
    items: list[dict[str, Any]],
    weather: dict[str, Any],
    *,
    cdh_reference: float = 0.0,
    hdh_reference: float = 0.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}
    temperatures = [float(value) for value in weather["temp_c"]]
    if len(temperatures) != 24:
        raise ValueError("Weather must contain 24 hourly temperatures")
    cdh_day = _degree_hours(weather, COMFORT_SETPOINT_C)
    hdh_day = _degree_hours(weather, 18.0, heating=True)
    mean_temp = sum(temperatures) / 24
    weather_weights = [max(0.0, temperature - COMFORT_SETPOINT_C) for temperature in temperatures]
    type_hourly: dict[str, list[float]] = defaultdict(lambda: [0.0] * 24)
    type_daily: dict[str, float] = defaultdict(float)
    comfort_total = 0.0
    fixed_total = 0.0

    for item in items:
        kind = str(item.get("type") or "other")
        qty = max(1, int(item.get("qty", item.get("count", 1))))
        watts = max(0.0, float(item.get("watts") or 0))
        duty = _clamp(float(item.get("duty_factor", 1.0)), 0.0, 1.0)
        schedule = _schedule(item)
        stated_hours = sum(schedule)
        override_hours = context.get("appliance_hours", {}).get(kind)
        if override_hours is not None:
            stated_hours = _clamp(float(override_hours), 0.0, 24.0)
        if kind == "ac" and context.get("ac_hours") is not None:
            stated_hours = _clamp(float(context["ac_hours"]), 0.0, 24.0)
        if stated_hours > 0 and sum(schedule) <= 0:
            schedule = default_hourly_use(kind, stated_hours)

        factor = 1.0
        target_hours = stated_hours
        if kind in AC_TYPES:
            if cdh_reference > 0.5:
                factor = _clamp(cdh_day / cdh_reference, DEMAND_FACTOR_MIN, DEMAND_FACTOR_MAX)
                target_hours = stated_hours * factor
            else:
                target_hours = min(24.0, cdh_day / 10.0)
        elif kind in FAN_TYPES:
            relative_cdh = cdh_day / cdh_reference if cdh_reference > 0.5 else cdh_day / 40.0
            factor = _clamp(0.3 + 0.7 * relative_cdh, FAN_MIN_FACTOR, 1.5)
            target_hours = stated_hours * factor
        elif kind == "geyser":
            if hdh_reference > 0.5:
                factor = _clamp(hdh_day / hdh_reference, DEMAND_FACTOR_MIN, DEMAND_FACTOR_MAX)
            target_hours = stated_hours * factor
        elif kind in {"refrigerator", "deep_freezer"}:
            factor = _clamp(1 + 0.015 * (mean_temp - 25), 0.9, 1.2)
            target_hours = stated_hours * factor

        if kind in COMFORT_TYPES:
            base_shape = _shape_to_hours(schedule, 1.0)
            weather_shape = _shape_to_hours(weather_weights, 1.0)
            shape = [
                0.5 * base + 0.5 * weather_weight
                for base, weather_weight in zip(base_shape, weather_shape, strict=True)
            ]
            hourly_hours = _shape_to_hours(shape, target_hours)
        else:
            hourly_hours = _shape_to_hours(schedule, target_hours)

        kwh_per_hour = [qty * watts / 1000 * duty * hours for hours in hourly_hours]
        if context.get("guests") and kind in LIGHT_TV_TYPES | FAN_TYPES:
            kwh_per_hour = [value * 1.1 for value in kwh_per_hour]

        scale = float(context.get("comfort_scale", 1.0)) if kind in COMFORT_TYPES else float(context.get("fixed_scale", 1.0))
        global_scale = float(context.get("global_scale", 1.0))
        kwh_per_hour = [
            value * _clamp(scale, 0.5, 2.0) * _clamp(global_scale, 0.2, 2.0)
            for value in kwh_per_hour
        ]
        total = sum(kwh_per_hour)
        type_daily[kind] += total
        type_hourly[kind] = [
            aggregate + value
            for aggregate, value in zip(type_hourly[kind], kwh_per_hour, strict=True)
        ]
        if kind in COMFORT_TYPES:
            comfort_total += total
        else:
            fixed_total += total

    potential_total = fixed_total + comfort_total
    outage_hours = _clamp(float(context.get("outage_hours") or 0.0), 0.0, 24.0)
    outage_fraction = outage_hours / 24.0
    hourly_kwh = [
        sum(type_hourly[kind][hour] for kind in type_hourly) * (1 - outage_fraction)
        for hour in range(24)
    ]
    delivered_total = sum(hourly_kwh)
    delivered_ratio = delivered_total / potential_total if potential_total > 0 else 0.0
    delivered_by_type = {
        kind: round(value * delivered_ratio, 3) for kind, value in type_daily.items()
    }
    return {
        "hourly_kwh": hourly_kwh,
        "by_type": delivered_by_type,
        "fixed_kwh": fixed_total * delivered_ratio,
        "comfort_kwh": comfort_total * delivered_ratio,
        "unserved_kwh": max(0.0, potential_total - delivered_total),
        "potential_kwh": potential_total,
        "cdh": cdh_day,
        "hdh": hdh_day,
        "mean_temp_c": mean_temp,
        "type_hourly": dict(type_hourly),
    }


def predict_demand(
    items: list[dict[str, Any]],
    weather: dict[str, Any],
    *,
    cdh_reference: float = 0.0,
    hdh_reference: float = 0.0,
    context: dict[str, Any] | None = None,
    n_days: int = 0,
    residual_std: float | None = None,
) -> dict[str, Any]:
    components = demand_components(
        items,
        weather,
        cdh_reference=cdh_reference,
        hdh_reference=hdh_reference,
        context=context,
    )
    total = sum(components["hourly_kwh"])
    if residual_std is not None and n_days >= 5:
        margin = 1.28 * max(0.0, residual_std)
    else:
        margin = total * 0.25
    if n_days < 5:
        confidence = "low"
    elif n_days <= 14:
        confidence = "medium"
    elif residual_std is not None and residual_std / max(total, 1e-6) < 0.15:
        confidence = "high"
    else:
        confidence = "medium"

    drivers: list[str] = []
    cdh_ref_safe = max(0.0, cdh_reference)
    if components["cdh"] > cdh_ref_safe * 1.15 and cdh_ref_safe > 0:
        drivers.append(
            f"Hotter than your reference day: cooling demand is estimated to rise by {max(0, components['cdh'] / cdh_ref_safe - 1) * 100:.0f}%."
        )
    elif cdh_ref_safe > 0 and components["cdh"] < cdh_ref_safe * 0.85:
        drivers.append("Cooler than your reference day, so cooling demand may be lower.")
    if (context or {}).get("guests"):
        drivers.append("Guests add an estimated 10% to lights, fans, and TV use.")
    if (context or {}).get("ac_hours") is not None:
        drivers.append(f"Your check-in set AC use to {float(context['ac_hours']):g} hours.")
    if (context or {}).get("outage_hours"):
        drivers.append(
            "Outage timing was not provided; unserved energy is estimated proportionally across the day."
        )
    if not drivers:
        drivers.append("Estimate uses appliance schedules and the day's weather.")
    if n_days < 5:
        drivers.append("Low confidence: fewer than five days of home history are available.")

    return {
        "hourly_kw": [round(value, 3) for value in components["hourly_kwh"]],
        "total_kwh": round(total, 2),
        "low_kwh": round(max(0.0, total - margin), 2),
        "high_kwh": round(total + margin, 2),
        "by_type": components["by_type"],
        "drivers": drivers,
        "confidence": confidence,
        "unserved_kwh": round(components["unserved_kwh"], 2),
        "fixed_kwh": round(components["fixed_kwh"], 2),
        "comfort_kwh": round(components["comfort_kwh"], 2),
        "cdh": round(components["cdh"], 2),
    }


def fit_personal_scales(
    observations: list[dict[str, float]],
    ridge_lambda: float = RIDGE_LAMBDA,
) -> dict[str, Any]:
    if not observations:
        return {"s_ac": 1.0, "s_other": 1.0, "residual_std": None, "n_days": 0}
    fixed = [float(item["fixed_kwh"]) for item in observations]
    comfort = [float(item["comfort_kwh"]) for item in observations]
    actual = [float(item["actual_kwh"]) for item in observations]
    a11 = sum(value * value for value in fixed) + ridge_lambda
    a12 = sum(one * two for one, two in zip(fixed, comfort, strict=True))
    a22 = sum(value * value for value in comfort) + ridge_lambda
    b1 = sum(value * observed for value, observed in zip(fixed, actual, strict=True)) + ridge_lambda
    b2 = sum(value * observed for value, observed in zip(comfort, actual, strict=True)) + ridge_lambda
    determinant = a11 * a22 - a12 * a12
    if abs(determinant) < 1e-9:
        other_scale = comfort_scale = 1.0
    else:
        other_scale = (b1 * a22 - b2 * a12) / determinant
        comfort_scale = (a11 * b2 - a12 * b1) / determinant
    other_scale = _clamp(other_scale, 0.5, 2.0)
    comfort_scale = _clamp(comfort_scale, 0.5, 2.0)
    residuals = [
        observed - fixed_value * other_scale - comfort_value * comfort_scale
        for fixed_value, comfort_value, observed in zip(fixed, comfort, actual, strict=True)
    ]
    residual_std = math.sqrt(sum(value * value for value in residuals) / len(residuals))
    return {
        "s_ac": round(comfort_scale, 4),
        "s_other": round(other_scale, 4),
        "residual_std": round(residual_std, 4),
        "n_days": len(observations),
    }


def robust_residual_std(residuals: list[float], expected_values: list[float]) -> float:
    if not residuals:
        return 0.0
    center = median(residuals)
    mad = median([abs(value - center) for value in residuals])
    floor = 0.1 * median([max(0.0, value) for value in expected_values])
    return max(1.4826 * mad, floor, 1e-6)
