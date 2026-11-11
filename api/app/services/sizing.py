from collections import defaultdict
from math import ceil
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STANDARD_INVERTER_SIZES = [
    1,
    1.5,
    2,
    3,
    3.6,
    4,
    5,
    6,
    8,
    10,
    12,
    15,
    20,
]
FALLBACK_ESSENTIAL_TYPES = {
    "refrigerator",
    "deep_freezer",
    "led_bulb",
    "tube_light",
    "ceiling_fan",
    "router",
    "phone_charger",
}


class LoadItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    qty: int = Field(default=1, ge=1)
    watts: float = Field(ge=0)
    duty_factor: float = Field(default=1.0, gt=0, le=1)
    surge_factor: float = Field(default=1.0, ge=1)
    hourly_use: list[float]
    is_essential: bool = False

    @field_validator("hourly_use")
    @classmethod
    def validate_hourly_use(cls, value: list[float]) -> list[float]:
        if len(value) != 24:
            raise ValueError("hourly_use must contain exactly 24 values")
        if any(hour < 0 or hour > 1 for hour in value):
            raise ValueError("hourly_use values must be between 0 and 1")
        return value


class SizingAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    peak_sun_hours: float = Field(default=5.0, gt=0)
    system_efficiency: float = Field(default=0.75, gt=0, le=1)
    inverter_margin: float = Field(default=1.25, gt=0)
    cloud_margin_offgrid: float = Field(default=1.15, gt=0)
    hybrid_panel_margin: float = Field(default=1.10, gt=0)
    battery_dod: float = Field(default=0.80, gt=0, le=1)
    battery_efficiency: float = Field(default=0.90, gt=0, le=1)
    autonomy_days: float = Field(default=1.0, gt=0)
    outage_hours: float = Field(default=4.0, gt=0)
    on_grid_offset: float = Field(default=1.0, gt=0)
    night_start_hour: int = Field(default=18, ge=0, le=23)
    night_end_hour: int = Field(default=7, ge=0, le=23)

    @model_validator(mode="after")
    def validate_night_window(self) -> "SizingAssumptions":
        if self.night_start_hour == self.night_end_hour:
            raise ValueError("night_start_hour and night_end_hour must differ")
        return self


class SystemOption(BaseModel):
    kind: Literal["off_grid", "hybrid", "on_grid"]
    panel_kw: float
    inverter_kw: float
    battery_kwh: float
    notes: list[str]


class SizingResult(BaseModel):
    daily_kwh: float
    day_kwh: float
    night_kwh: float
    connected_kw: float
    peak_kw: float
    load_profile_kw: list[float]
    running_profile_kw: list[float]
    options: list[SystemOption]
    breakdown: list[dict]
    assumptions: dict
    warnings: list[str]


def size_system(
    items: list[LoadItem], assumptions: SizingAssumptions | None = None
) -> SizingResult:
    """Size on-grid, hybrid, and off-grid systems from loads measured in W and kWh."""
    assumptions = assumptions or SizingAssumptions()
    warnings: list[str] = []
    if not items:
        warnings.append("No appliances added yet.")

    hourly_energy = [0.0] * 24
    running_profile = [0.0] * 24
    essential_profile = [0.0] * 24
    breakdown_energy: dict[str, float] = defaultdict(float)
    daily_kwh = 0.0
    night_kwh = 0.0
    connected_watts = 0.0
    ac_count = 0
    max_single_watts = 0.0
    max_startup_extra_kw = 0.0

    for item in items:
        item_energy = 0.0
        connected_watts += item.qty * item.watts
        max_single_watts = max(max_single_watts, item.watts)
        max_startup_extra_kw = max(
            max_startup_extra_kw,
            item.watts / 1000 * (item.surge_factor - 1),
        )
        if item.type == "ac":
            ac_count += item.qty

        for hour, fraction_on in enumerate(item.hourly_use):
            energy = (
                item.qty
                * item.watts
                / 1000
                * item.duty_factor
                * fraction_on
            )
            running = item.qty * item.watts / 1000 * fraction_on
            item_energy += energy
            hourly_energy[hour] += energy
            running_profile[hour] += running
            if item.is_essential:
                essential_profile[hour] += running

        daily_kwh += item_energy
        breakdown_energy[item.type] += item_energy

    is_night = [
        hour >= assumptions.night_start_hour or hour < assumptions.night_end_hour
        if assumptions.night_start_hour > assumptions.night_end_hour
        else assumptions.night_start_hour <= hour < assumptions.night_end_hour
        for hour in range(24)
    ]
    night_kwh = sum(
        hourly_energy[hour] for hour in range(24) if is_night[hour]
    )
    day_kwh = sum(
        hourly_energy[hour] for hour in range(24) if not is_night[hour]
    )

    peak_kw = max(running_profile, default=0.0) + max_startup_extra_kw
    required_inverter_kw = peak_kw * assumptions.inverter_margin
    inverter_kw = _standard_inverter_size(required_inverter_kw)
    connected_kw = connected_watts / 1000

    if ac_count > 4:
        warnings.append("More than 4 ACs listed; please verify quantities.")
    if connected_kw > 15:
        warnings.append("Connected load is above 15 kW; check the appliance list.")
    if max_single_watts > 5000:
        warnings.append("A single appliance is above 5 kW; please verify its rating.")
    if peak_kw > 10:
        warnings.append("Peak load is above 10 kW; check sanctioned load / 3-phase.")
    if required_inverter_kw > 20:
        warnings.append("Inverter needs custom/3-phase design.")
    if daily_kwh > 60:
        warnings.append("Daily energy is unusually high; re-check hours and quantities.")

    explicit_essential = any(item.is_essential for item in items)
    hybrid_peak_kw = max(essential_profile, default=0.0)
    hybrid_notes: list[str] = []
    if not explicit_essential:
        hybrid_peak_kw = max(
            (
                sum(
                    item.qty * item.watts / 1000 * item.hourly_use[hour]
                    for item in items
                    if item.type in FALLBACK_ESSENTIAL_TYPES
                )
                for hour in range(24)
            ),
            default=0.0,
        )
        hybrid_notes.append(
            "No essential loads were selected; common essentials were assumed."
        )

    base_panel_kw = daily_kwh * assumptions.on_grid_offset / (
        assumptions.peak_sun_hours * assumptions.system_efficiency
    )
    battery_denominator = assumptions.battery_dod * assumptions.battery_efficiency
    options = [
        SystemOption(
            kind="off_grid",
            panel_kw=_round2(
                daily_kwh
                / (assumptions.peak_sun_hours * assumptions.system_efficiency)
                * assumptions.cloud_margin_offgrid
            ),
            inverter_kw=inverter_kw,
            battery_kwh=_round2(
                night_kwh * assumptions.autonomy_days / battery_denominator
            ),
            notes=[],
        ),
        SystemOption(
            kind="hybrid",
            panel_kw=_round2(base_panel_kw * assumptions.hybrid_panel_margin),
            inverter_kw=inverter_kw,
            battery_kwh=_round2(
                hybrid_peak_kw * assumptions.outage_hours / battery_denominator
            ),
            notes=hybrid_notes,
        ),
        SystemOption(
            kind="on_grid",
            panel_kw=_round2(base_panel_kw),
            inverter_kw=inverter_kw,
            battery_kwh=0,
            notes=[],
        ),
    ]
    breakdown = [
        {
            "type": appliance_type,
            "kwh": _round3(energy),
            "share": _round3(energy / daily_kwh) if daily_kwh else 0.0,
        }
        for appliance_type, energy in sorted(
            breakdown_energy.items(), key=lambda entry: entry[1], reverse=True
        )
    ]

    return SizingResult(
        daily_kwh=_round3(daily_kwh),
        day_kwh=_round3(day_kwh),
        night_kwh=_round3(night_kwh),
        connected_kw=_round3(connected_kw),
        peak_kw=_round3(peak_kw),
        load_profile_kw=[_round3(value) for value in hourly_energy],
        running_profile_kw=[_round3(value) for value in running_profile],
        options=options,
        breakdown=breakdown,
        assumptions=assumptions.model_dump(),
        warnings=warnings,
    )


def _standard_inverter_size(required_kw: float) -> float:
    if required_kw == 0:
        return 0.0
    for standard_size in STANDARD_INVERTER_SIZES:
        if standard_size >= required_kw:
            return standard_size
    return float(ceil(required_kw / 5) * 5)


def _round2(value: float) -> float:
    return round(value + 1e-10, 2)


def _round3(value: float) -> float:
    return round(value + 1e-10, 3)
