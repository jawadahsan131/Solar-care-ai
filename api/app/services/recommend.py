from __future__ import annotations

from typing import Any

FLEXIBLE_TYPES = {
    "washing_machine",
    "iron",
    "water_pump",
    "geyser",
    "vacuum_cleaner",
    "electric_oven",
    "ups",
}
BLOCK_LOAD_TYPES = {"washing_machine", "iron", "vacuum_cleaner", "electric_oven"}
SPLIT_LOAD_TYPES = {"water_pump", "geyser", "ups"}


def _grid_import(load: list[float], solar: list[float]) -> float:
    return sum(max(0.0, demand - generation) for demand, generation in zip(load, solar, strict=True))


def _item_curve(item: dict[str, Any]) -> list[float]:
    schedule = item.get("hourly_use")
    if not isinstance(schedule, list) or len(schedule) != 24:
        return [0.0] * 24
    power = (
        max(1, int(item.get("qty", 1)))
        * max(0.0, float(item.get("watts") or 0))
        / 1000
        * max(0.0, float(item.get("duty_factor", 1.0)))
    )
    return [power * max(0.0, min(1.0, float(value))) for value in schedule]


def _blocked(
    item_id: str,
    start: int,
    duration: int,
    blocked_windows: list[dict[str, Any]],
) -> bool:
    candidate_hours = {(start + offset) % 24 for offset in range(duration)}
    for window in blocked_windows:
        if window.get("item_id") != item_id:
            continue
        if candidate_hours.intersection(window.get("hours", [])):
            return True
    return False


def _candidate_profiles(
    item: dict[str, Any],
    move_energy: float,
    current_curve: list[float],
    plan_load: list[float],
    solar_kw: list[float],
    allowed_start: int,
    allowed_end: int,
    quiet_hours: set[int],
    blocked_windows: list[dict[str, Any]],
) -> list[tuple[list[int], list[float], float]]:
    item_id = str(item.get("id") or item.get("type") or "load")
    allowed_hours = [
        hour
        for hour in range(allowed_start, allowed_end)
        if hour not in quiet_hours
    ]
    if not allowed_hours:
        return []
    current_power = max(current_curve, default=0.0)
    if current_power <= 0:
        current_power = move_energy
    duration = max(1, sum(1 for value in current_curve if value > 0))
    duration = min(duration, len(allowed_hours))

    candidates: list[tuple[list[int], list[float], float]] = []
    if str(item.get("type")) in SPLIT_LOAD_TYPES:
        ranked_hours = sorted(
            allowed_hours,
            key=lambda hour: max(0.0, solar_kw[hour] - plan_load[hour]),
            reverse=True,
        )
        hours_needed = move_energy / current_power if current_power > 0 else 0
        selected: list[int] = []
        profile = [0.0] * 24
        remaining = move_energy
        for hour in ranked_hours:
            if remaining <= 1e-9:
                break
            if _blocked(item_id, hour, 1, blocked_windows):
                continue
            amount = min(current_power, remaining)
            profile[hour] = amount
            selected.append(hour)
            remaining -= amount
        if selected and remaining <= 1e-9:
            candidates.append((selected, profile, hours_needed))
        return candidates

    if duration > len(allowed_hours):
        return []
    curve_power = move_energy / duration
    for start_index in range(0, len(allowed_hours) - duration + 1):
        hours = allowed_hours[start_index : start_index + duration]
        if hours != list(range(hours[0], hours[0] + duration)):
            continue
        if _blocked(item_id, hours[0], duration, blocked_windows):
            continue
        profile = [0.0] * 24
        for hour in hours:
            profile[hour] = curve_power
        candidates.append((hours, profile, float(duration)))
    return candidates


def optimize_plan(
    solar_kw: list[float],
    load_kw: list[float],
    appliances: list[dict[str, Any]],
    *,
    allowed_start: int = 8,
    allowed_end: int = 20,
    quiet_hours: set[int] | None = None,
    blocked_windows: list[dict[str, Any]] | None = None,
    battery_kwh: float | None = None,
    mean_cloud_pct: float | None = None,
    unserved_kwh: float = 0.0,
) -> dict[str, Any]:
    if len(solar_kw) != 24 or len(load_kw) != 24:
        raise ValueError("Solar and load profiles must contain 24 hourly values")
    if not 0 <= allowed_start < allowed_end <= 24:
        raise ValueError("Allowed hours must form a valid same-day window")
    solar = [max(0.0, float(value)) for value in solar_kw]
    original_load = [max(0.0, float(value)) for value in load_kw]
    plan_load = list(original_load)
    quiet = quiet_hours or set()
    blocked = blocked_windows or []
    original_grid_import = _grid_import(original_load, solar)
    recommendations: list[dict[str, Any]] = []

    candidates = []
    for item in appliances:
        kind = str(item.get("type") or "")
        if kind not in FLEXIBLE_TYPES:
            continue
        curve = _item_curve(item)
        energy = sum(curve)
        if energy > 0:
            candidates.append((energy, item, curve))
    candidates.sort(key=lambda entry: entry[0], reverse=True)

    for _, item, current_curve in candidates:
        item_id = str(item.get("id") or item.get("type") or "load")
        removed_curve = [
            min(plan_load[hour], current_curve[hour]) for hour in range(24)
        ]
        move_energy = sum(removed_curve)
        if move_energy <= 0:
            continue
        base_load = [
            max(0.0, plan_load[hour] - removed_curve[hour])
            for hour in range(24)
        ]
        placements = _candidate_profiles(
            item,
            move_energy,
            removed_curve,
            base_load,
            solar,
            allowed_start,
            allowed_end,
            quiet,
            blocked,
        )
        if not placements:
            continue
        before = _grid_import(plan_load, solar)
        best = None
        for hours, profile, _ in placements:
            proposed = [base_load[hour] + profile[hour] for hour in range(24)]
            saved = before - _grid_import(proposed, solar)
            if best is None or saved > best[0]:
                best = (saved, hours, profile, proposed)
        if best is None:
            continue
        saved, destination_hours, moved_curve, proposed_load = best
        minimum_saving = max(0.2, move_energy * 0.1)
        if saved + 1e-9 < minimum_saving:
            continue
        original_hours = [hour for hour, value in enumerate(removed_curve) if value > 0]
        plan_load = proposed_load
        kind = str(item["type"])
        recommendation_id = f"{item_id}@{','.join(map(str, original_hours))}@{','.join(map(str, destination_hours))}"
        recommendations.append(
            {
                "id": recommendation_id,
                "appliance_type": kind,
                "title": f"Run {kind.replace('_', ' ')} around {min(destination_hours):02d}:00 instead",
                "from_hours": original_hours,
                "to_hours": destination_hours,
                "kwh_moved": round(move_energy, 3),
                "grid_import_saved_kwh": round(saved, 3),
                "reason": "This time overlaps more available solar after accounting for the other planned loads.",
                "difficulty": "easy" if kind in {"washing_machine", "water_pump", "geyser", "ups"} else "hard",
            }
        )
        if len(recommendations) == 5:
            break

    recommendations.sort(key=lambda item: item["grid_import_saved_kwh"], reverse=True)
    total_solar = sum(solar)
    total_load = sum(original_load)
    direct_solar = sum(min(load, generation) for load, generation in zip(original_load, solar, strict=True))
    evening_deficit = sum(
        max(0.0, original_load[hour] - solar[hour])
        for hour in list(range(18, 24)) + list(range(0, 6))
    )
    metrics = {
        "self_consumption_pct": round(100 * direct_solar / total_solar, 1) if total_solar else 0.0,
        "solar_coverage_pct": round(100 * direct_solar / total_load, 1) if total_load else 0.0,
        "evening_deficit_kwh": round(evening_deficit, 2),
        "grid_import_kwh": round(original_grid_import, 2),
        "plan_grid_import_kwh": round(_grid_import(plan_load, solar), 2),
        "total_load_kwh": round(total_load, 2),
        "plan_total_load_kwh": round(sum(plan_load), 2),
    }

    tips = []
    if battery_kwh is not None and evening_deficit > max(0.0, battery_kwh):
        tips.append(
            {
                "type": "battery",
                "text": (
                    f"Estimated evening deficit exceeds the stated battery by "
                    f"{evening_deficit - battery_kwh:.1f} kWh; that portion may need grid support."
                ),
            }
        )
    if mean_cloud_pct is not None and mean_cloud_pct >= 70:
        tips.append(
            {"type": "weather", "text": "Tomorrow looks cloudy; plan lighter use where practical."}
        )
    if unserved_kwh > 0:
        tips.append(
            {
                "type": "outage",
                "text": f"About {unserved_kwh:.1f} kWh may be unserved during outages; exact timing is unknown.",
            }
        )
    if any(str(item.get("type")) == "ac" for item in appliances):
        tips.append(
            {
                "type": "comfort",
                "text": "Experimental: if comfortable, pre-cool during 11:00–15:00 and relax the setpoint later; savings are not reliably quantified yet.",
            }
        )
    return {
        "metrics": metrics,
        "plan_load_kw": [round(value, 3) for value in plan_load],
        "recommendations": recommendations,
        "tips": tips,
    }
