Claude

















03 chunk3 sizing engine · MD
CHUNK 3 — Sizing engine (pure Python + tests)
(Paste MASTER BRIEF first, then this card. No database, no web, no API in this chunk. A pure library that other chunks import.)

Goal
api/app/services/sizing.py and api/tests/test_sizing.py. Given a list of loads and assumptions, return daily energy, peak load, inverter, panels, battery for three options (off_grid, hybrid, on_grid), plus an hourly load profile, a per-appliance breakdown, assumptions, and warnings.

Files to write (one at a time)
api/app/services/sizing.py
api/app/services/schedules.py (default hourly schedules)
api/tests/test_sizing.py
A short docs/sizing.md explaining formulas in plain language (for the course report).
Models (Pydantic v2)
python
class LoadItem(BaseModel):
    type: str
    qty: int = 1
    watts: float                 # running input power, W
    duty_factor: float = 1.0
    surge_factor: float = 1.0
    hourly_use: list[float]      # 24 values, each 0..1
    is_essential: bool = False

class SizingAssumptions(BaseModel):
    peak_sun_hours: float = 5.0
    system_efficiency: float = 0.75
    inverter_margin: float = 1.25
    cloud_margin_offgrid: float = 1.15
    hybrid_panel_margin: float = 1.10
    battery_dod: float = 0.80
    battery_efficiency: float = 0.90
    autonomy_days: float = 1.0
    outage_hours: float = 4.0
    on_grid_offset: float = 1.0
    night_start_hour: int = 18
    night_end_hour: int = 7      # night = hours >= 18 or < 7

class SystemOption(BaseModel):
    kind: Literal["off_grid","hybrid","on_grid"]
    panel_kw: float
    inverter_kw: float
    battery_kwh: float
    notes: list[str]

class SizingResult(BaseModel):
    daily_kwh: float; day_kwh: float; night_kwh: float
    connected_kw: float          # sum of qty*watts/1000 (all appliances)
    peak_kw: float
    load_profile_kw: list[float] # 24 values: average kW per hour WITH duty factor
    running_profile_kw: list[float] # 24 values WITHOUT duty (used for peak)
    options: list[SystemOption]
    breakdown: list[dict]        # per type: kwh, share (0..1), sorted descending
    assumptions: dict
    warnings: list[str]
Function: size_system(items: list[LoadItem], assumptions: SizingAssumptions | None = None) -> SizingResult.

Formulas
Exactly as MASTER BRIEF section 8. Standard inverter sizes [1,1.5,2,3,3.6,4,5,6,8,10,12,15,20]; if the needed size exceeds 20 kW, return the needed value rounded up to the next 5 kW and add a warning "needs custom/3-phase design". Hybrid battery uses only is_essential items; if no item is essential, assume appliances of types refrigerator, deep_freezer, led_bulb, tube_light, ceiling_fan, router, phone_charger count as essential and add a note saying so.

Default schedules (schedules.py)
default_hourly_use(type: str, hours_per_day: float) -> list[float] Place hours consecutively starting at a start hour per type (wrapping past midnight); the last hour may be a fraction. If hours_per_day >= 24 return all 1.0. If 0 return all 0. Start hours: ac 15, ceiling_fan 10, pedestal_fan 10, exhaust_fan 18, air_cooler 12, refrigerator 0, deep_freezer 0, microwave 19, electric_oven 19, water_dispenser 0, electric_kettle 7, washing_machine 10, iron 9, geyser 6, water_pump 6, tv 19, desktop_pc 10, laptop 10, router 0, ups 0, led_bulb 18, tube_light 18, phone_charger 22, vacuum_cleaner 10, other 12. (The human may adjust these.)

Validation and warnings
hourly_use length must be 24 and values within 0..1, else raise ValueError with a clear message.
qty >= 1, watts >= 0, duty in (0,1], surge >= 1.
Warnings (strings, user-friendly): no appliances; more than 4 ACs; connected_kw above 15; a single appliance above 5 kW; hours_per_day above 24 impossible; peak_kw above 10 ("check sanctioned load / 3-phase"); daily_kwh above 60 ("unusually high, please re-check hours and quantities").
Worked example for the tests (hand-calculated; the tests must reproduce these numbers)
Items:

AC: qty 1, watts 1200, duty 0.6, surge 2.0, hourly_use 1.0 for hours 13..20 (8 hours), else 0
Fans: qty 3, watts 75, duty 1.0, surge 1.5, hourly_use 1.0 for hours 10..21 (12 hours), essential
Fridge: qty 1, watts 150, duty 0.4, surge 3.0, hourly_use all 1.0, essential
LED lights: qty 8, watts 12, duty 1.0, surge 1.0, hourly_use 1.0 for hours 18..23 (6 hours), essential
Expected (default assumptions):

daily_kwh = 10.476 (AC 5.76 + fans 2.7 + fridge 1.44 + lights 0.576)
night_kwh = 4.416 (AC 2.16 + fans 0.9 + fridge 0.78 + lights 0.576)
running_profile peak hour (hours 18-20) = 1.671 kW; start-up extra = 1.2 kW (AC); peak_kw = 2.871
inverter_kw = 3.6 (2.871 x 1.25 = 3.589 -> next standard size 3.6)
on_grid: panel_kw 2.79, battery 0
off_grid: panel_kw 3.21, battery_kwh 6.13
hybrid: panel_kw 3.07, battery_kwh 2.62 (essential peak 0.471 kW x 4 h / 0.72) Use pytest approx with tolerance 0.01.
Extra tests
Empty list returns zeros plus the "no appliances" warning (no crash).
Wrong hourly_use length raises ValueError.
default_hourly_use("ac", 8) sums to 8 and wraps past midnight correctly; default_hourly_use("refrigerator", 24) is all ones; fractional hours (2.5) sum to 2.5.
Changing peak_sun_hours to 6 reduces panel_kw proportionally.
Result is JSON-serializable (model_dump() works).
Acceptance
 pytest passes with no network and no database.
 No imports from FastAPI or Supabase in these files.
 Functions have docstrings listing units.
Handoff
HANDOFF NOTE with the public function names and any assumption you made.


