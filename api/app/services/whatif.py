from __future__ import annotations

import math
from calendar import monthrange
from collections.abc import Sequence
from typing import Any

from app.services.demand import demand_components
from app.services.solar import pv_curve
from app.services.tariff import estimated_import_cost

BATTERY_USABLE_FRACTION = 0.8
BATTERY_ROUND_TRIP_EFFICIENCY = 0.9
BATTERY_ONE_WAY_EFFICIENCY = math.sqrt(BATTERY_ROUND_TRIP_EFFICIENCY)
SEASONS = {
    "Winter": (12, 1, 2),
    "Spring": (3, 4, 5),
    "Summer": (6, 7, 8),
    "Autumn": (9, 10, 11),
}


def simulate_day(
    solar_kw: Sequence[float],
    load_kwh: Sequence[float],
    essential_load_kwh: Sequence[float],
    *,
    battery_kwh: float,
    inverter_kw: float,
    outage_hours: float,
) -> dict[str, Any]:
    if any(len(profile) != 24 for profile in (solar_kw, load_kwh, essential_load_kwh)):
        raise ValueError("Solar and load profiles must contain 24 hourly values")

    solar = [min(max(0.0, float(value)), inverter_kw) for value in solar_kw]
    load = [max(0.0, float(value)) for value in load_kwh]
    essential = [max(0.0, float(value)) for value in essential_load_kwh]
    capacity = battery_kwh * BATTERY_USABLE_FRACTION
    charge_limit = inverter_kw if inverter_kw > 0 else battery_kwh
    discharge_limit = charge_limit
    stored = 0.0
    direct_solar = 0.0
    solar_to_battery = 0.0
    grid_import = 0.0
    evening_battery_kwh = 0.0
    evening_grid_import = 0.0
    stored_at_sunset = 0.0

    for hour, (generation, demand) in enumerate(zip(solar, load, strict=True)):
        direct = min(generation, demand)
        direct_solar += direct
        surplus = generation - direct
        deficit = demand - direct
        if surplus > 0 and capacity > stored:
            charge_input = min(
                surplus,
                charge_limit,
                (capacity - stored) / BATTERY_ONE_WAY_EFFICIENCY,
            )
            stored += charge_input * BATTERY_ONE_WAY_EFFICIENCY
            solar_to_battery += charge_input
        elif deficit > 0 and stored > 0:
            discharge = min(
                deficit,
                discharge_limit,
                stored * BATTERY_ONE_WAY_EFFICIENCY,
            )
            stored -= discharge / BATTERY_ONE_WAY_EFFICIENCY
            grid_import += deficit - discharge
            if 18 <= hour < 24:
                evening_battery_kwh += discharge
        else:
            grid_import += deficit
        if 18 <= hour < 24:
            evening_grid_import += max(0.0, demand - direct)
        if hour == 17:
            stored_at_sunset = stored

    covered_outage_hours = 0.0
    remaining_outage = max(0.0, min(24.0, outage_hours))
    outage_storage = stored_at_sunset
    outage_hours_to_check = range(24) if sum(essential) > 0 else ()
    for offset in outage_hours_to_check:
        duration = min(1.0, remaining_outage)
        if duration <= 0:
            break
        hour = (18 + offset) % 24
        required = essential[hour] * duration
        if required <= 1e-9:
            covered_outage_hours += duration
            remaining_outage -= duration
            continue
        available = min(
            required,
            discharge_limit * duration,
            outage_storage * BATTERY_ONE_WAY_EFFICIENCY,
        )
        outage_storage -= available / BATTERY_ONE_WAY_EFFICIENCY
        covered_outage_hours += available / required * duration
        remaining_outage -= duration
        if available + 1e-9 < required:
            break

    total_solar = sum(solar)
    total_load = sum(load)
    baseline_import = total_load
    return {
        "solar_kwh": total_solar,
        "load_kwh": total_load,
        "grid_import_kwh": grid_import,
        "baseline_grid_import_kwh": baseline_import,
        "solar_used_kwh": direct_solar + solar_to_battery,
        "evening_battery_kwh": evening_battery_kwh,
        "evening_grid_import_kwh": evening_grid_import,
        "outage_coverage_hours": min(outage_hours, covered_outage_hours),
        "solar_profile_kw": solar,
        "load_profile_kw": load,
    }


def _simulate_month(
    weather: dict[str, Sequence[float]],
    appliances: list[dict[str, Any]],
    *,
    panel_kw: float,
    battery_kwh: float,
    inverter_kw: float,
    outage_hours: float,
    sun_scale: float,
    demand_scale: float,
) -> dict[str, Any]:
    demand = demand_components(appliances, weather)
    base_load = demand["hourly_kwh"]
    load = [value * demand_scale for value in base_load]
    essentials = [item for item in appliances if item.get("is_essential")]
    essential_load = (
        demand_components(essentials, weather)["hourly_kwh"]
        if essentials
        else base_load
    )
    essential_load = [value * demand_scale for value in essential_load]
    solar = [
        value * panel_kw * sun_scale
        for value in pv_curve(weather["ghi_wm2"], weather["temp_c"])
    ]
    return simulate_day(
        solar,
        load,
        essential_load,
        battery_kwh=battery_kwh,
        inverter_kw=inverter_kw,
        outage_hours=outage_hours,
    )


def _annual_variant(
    monthly_weather: list[tuple[int, dict[str, Sequence[float]]]],
    appliances: list[dict[str, Any]],
    *,
    panel_kw: float,
    battery_kwh: float,
    inverter_kw: float,
    outage_hours: float,
    sun_scale: float,
    demand_scale: float,
    tariff: dict[str, Any] | None,
) -> dict[str, Any]:
    solar_total = load_total = grid_total = baseline_total = solar_used = 0.0
    evening_total = outage_total = 0.0
    annual_saving = 0.0
    weighted_days = 0
    month_imports: list[tuple[int, float, float]] = []
    seasonal_profiles: dict[str, list[dict[str, Any]]] = {
        season: [] for season in SEASONS
    }

    for month, weather in monthly_weather:
        days = monthrange(2025, month)[1]
        result = _simulate_month(
            weather,
            appliances,
            panel_kw=panel_kw,
            battery_kwh=battery_kwh,
            inverter_kw=inverter_kw,
            outage_hours=outage_hours,
            sun_scale=sun_scale,
            demand_scale=demand_scale,
        )
        solar_total += result["solar_kwh"] * days
        load_total += result["load_kwh"] * days
        grid_total += result["grid_import_kwh"] * days
        baseline_total += result["baseline_grid_import_kwh"] * days
        solar_used += result["solar_used_kwh"] * days
        evening_total += result["evening_battery_kwh"] * days
        outage_total += result["outage_coverage_hours"] * days
        weighted_days += days
        month_imports.append(
            (
                days,
                result["baseline_grid_import_kwh"] * days,
                result["grid_import_kwh"] * days,
            )
        )
        for season, months in SEASONS.items():
            if month in months:
                seasonal_profiles[season].append(result)
                break

    if tariff is not None:
        annual_saving = sum(
            max(
                0.0,
                estimated_import_cost(before, tariff)
                - estimated_import_cost(after, tariff),
            )
            for _, before, after in month_imports
        )

    return {
        "yearly_solar_kwh": round(solar_total, 1),
        "yearly_load_kwh": round(load_total, 1),
        "solar_coverage_pct": round(
            100 * max(0.0, load_total - grid_total) / load_total, 1
        )
        if load_total
        else 0.0,
        "self_consumption_pct": round(100 * solar_used / solar_total, 1)
        if solar_total
        else 0.0,
        "grid_import_avoided_kwh": round(max(0.0, baseline_total - grid_total), 1),
        "yearly_bill_saving_pkr": round(annual_saving, 0)
        if tariff is not None
        else None,
        "evening_battery_kwh_per_year": round(evening_total, 1),
        "outage_coverage_hours": round(outage_total / weighted_days, 1)
        if weighted_days
        else 0.0,
        "seasonal_average_day": {
            season: {
                "solar_kw": [
                    round(
                        sum(day["solar_profile_kw"][hour] for day in days)
                        / len(days),
                        3,
                    )
                    for hour in range(24)
                ],
                "load_kw": [
                    round(
                        sum(day["load_profile_kw"][hour] for day in days)
                        / len(days),
                        3,
                    )
                    for hour in range(24)
                ],
            }
            for season, days in seasonal_profiles.items()
        },
    }


def compare_scenarios(
    monthly_weather: list[tuple[int, dict[str, Sequence[float]]]],
    appliances: list[dict[str, Any]],
    *,
    panel_kw: float,
    battery_kwh: float,
    inverter_kw: float | None,
    outage_hours: float,
    cost_per_kw_pkr: float | None,
    tariff: dict[str, Any] | None,
) -> dict[str, Any]:
    scenarios = [
        {
            "id": "grid_tied",
            "label": "Grid-tied",
            "panel_kw": panel_kw * 0.6,
            "battery_kwh": 0.0,
        },
        {
            "id": "hybrid",
            "label": "Hybrid",
            "panel_kw": panel_kw,
            "battery_kwh": battery_kwh,
        },
        {
            "id": "expanded",
            "label": "Expanded",
            "panel_kw": panel_kw * 1.6,
            "battery_kwh": battery_kwh * 1.5,
        },
    ]
    output = []
    seasonal_average_day = None
    for scenario in scenarios:
        system_inverter_kw = (
            inverter_kw if inverter_kw is not None else scenario["panel_kw"]
        )
        variants = {
            "low": _annual_variant(
                monthly_weather,
                appliances,
                panel_kw=scenario["panel_kw"],
                battery_kwh=scenario["battery_kwh"],
                inverter_kw=system_inverter_kw,
                outage_hours=outage_hours,
                sun_scale=0.9,
                demand_scale=1.15,
                tariff=tariff,
            ),
            "base": _annual_variant(
                monthly_weather,
                appliances,
                panel_kw=scenario["panel_kw"],
                battery_kwh=scenario["battery_kwh"],
                inverter_kw=system_inverter_kw,
                outage_hours=outage_hours,
                sun_scale=1.0,
                demand_scale=1.0,
                tariff=tariff,
            ),
            "high": _annual_variant(
                monthly_weather,
                appliances,
                panel_kw=scenario["panel_kw"],
                battery_kwh=scenario["battery_kwh"],
                inverter_kw=system_inverter_kw,
                outage_hours=outage_hours,
                sun_scale=1.1,
                demand_scale=0.85,
                tariff=tariff,
            ),
        }
        investment = (
            scenario["panel_kw"] * cost_per_kw_pkr
            if cost_per_kw_pkr is not None
            else None
        )
        low_saving = variants["low"]["yearly_bill_saving_pkr"]
        high_saving = variants["high"]["yearly_bill_saving_pkr"]
        payback = None
        if investment is not None and low_saving and high_saving:
            payback = {
                "low_years": round(investment / high_saving, 1),
                "high_years": round(investment / low_saving, 1),
            }
        output.append(
            {
                **scenario,
                "inverter_kw": system_inverter_kw,
                "estimated_investment_pkr": round(investment, 0)
                if investment is not None
                else None,
                "payback_range_years": payback,
                "sensitivity": variants,
            }
        )
        if scenario["id"] == "hybrid":
            seasonal_average_day = variants["base"]["seasonal_average_day"]

    return {
        "scenarios": output,
        "seasonal_average_day": seasonal_average_day or {},
        "sensitivity_assumptions": {
            "low": "Solar resource -10%; demand +15%.",
            "base": "Climate-normal solar resource and modeled appliance demand.",
            "high": "Solar resource +10%; demand -15%.",
        },
        "tariff_available": tariff is not None,
    }
