from __future__ import annotations

from typing import Any


def demand_features(
    appliances: list[dict[str, Any]],
    weather: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, float]:
    context = context or {}
    temperatures = [float(value) for value in weather.get("temp_c", [])]
    mean_temp = sum(temperatures) / len(temperatures) if temperatures else 0.0
    total_watts = sum(
        max(0.0, float(item.get("watts") or 0))
        * max(1, int(item.get("qty", item.get("count", 1))))
        for item in appliances
    )
    return {
        "mean_temp_c": mean_temp,
        "total_watts": total_watts,
        "ac_hours": float(context.get("ac_hours") or 0.0),
        "outage_hours": float(context.get("outage_hours") or 0.0),
        "guests": 1.0 if context.get("guests") else 0.0,
    }
