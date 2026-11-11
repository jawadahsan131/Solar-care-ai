# PART 2 — BRIEF ADDENDUM (paste right AFTER 00_MASTER_BRIEF.md in every Part 2 chat)
Master brief v2 still applies. This adds the Part 2 contracts. If they conflict, this addendum wins for Part 2 only.

## 1. What Part 2 is
No connection to real appliances. Inputs: (a) the verified appliance list from Part 1, (b) weather (history + forecast), (c) the user's tap-only daily check-in and optional meter/bill numbers. Outputs: (1) a daily consumption forecast (kWh, hourly) adjusted for weather, (2) a normal vs unusual verdict for each day, (3) hour-by-hour advice to move flexible loads into the solar hours, with the number of kWh saved, (4) a what-if view for a system size.
Principles: simple, explainable models first; every number says how it was derived; the user can correct everything; the user's data is never silently overwritten; show uncertainty (a range, not one number).

## 2. New tables (see sql/migrations/002_part2.sql, run in Supabase SQL Editor)
- `daily_logs` gains: `appliance_hours jsonb` ({type: hours}), `predicted_kwh numeric`, `weather jsonb` (daily summary), `source text` (user | synthetic).
- `weather_cache(lat2 numeric, lon2 numeric, day date, hourly jsonb, kind text, fetched_at)` primary key (lat2, lon2, day, kind); lat/lon rounded to 2 decimals; kind = forecast | archive.
- `demand_models(home_id pk, params jsonb, fitted_at, n_days int, metrics jsonb)`.
- `recommendation_feedback(id, home_id, day date, rec_id text, status text, created_at)` status = done | skipped | not_possible.

## 3. New shapes
HourlyWeather: 24 values each of temp_c, humidity_pct, cloud_pct, ghi_wm2 (global horizontal irradiance), index = local hour.
Forecast (GET): {day, source: forecast|archive, hourly: HourlyWeather, pv_kw_per_kwp: float[24], sun_hours: float, cdh: float, summary: str}
DemandPrediction: {day, hourly_kw: float[24], total_kwh, low_kwh, high_kwh, by_type: {type: kwh}, drivers: [str], confidence: low|medium|high}
DayVerdict: {day, actual_kwh?, expected_kwh, z, status: normal|high|low|unknown, reasons: [str]}
Recommendation: {id, appliance_type, title, from_hours: int[], to_hours: int[], kwh_moved, grid_import_saved_kwh, reason, difficulty: easy|medium|hard}

## 4. New endpoints (all need auth + home ownership check)
- POST /homes/{id}/bill (multipart image OR JSON {month, units_kwh}) ; GET /homes/{id}/bills ; GET /homes/{id}/calibration
- GET /homes/{id}/forecast?date=YYYY-MM-DD (also range days=1..7)
- POST /homes/{id}/checkin {date, ac_hours?, outage_hours?, guests?, meter_kwh?, appliance_hours?} (upsert by date) ; GET /homes/{id}/checkins?days=30
- GET /homes/{id}/demand?date= (DemandPrediction) ; GET /homes/{id}/verdicts?days=14
- GET /homes/{id}/recommendations?date= ; POST /homes/{id}/recommendations/{rec_id}/feedback
- POST /homes/{id}/whatif {panel_kw, battery_kwh?, tariff_overrides?}

## 5. Shared constants (api/app/services/part2_config.py, one file, easy to edit)
COMFORT_SETPOINT_C = 24; FAN_MIN_FACTOR = 0.3; DEMAND_FACTOR_MIN/MAX = 0.2 / 2.0; PV_PERFORMANCE_RATIO = 0.75; PV_TEMP_COEFF = -0.004 per C above 25 (cell temp = air temp + 20 at 800 W/m2, scaled by GHI/800); SOLAR_WINDOW = hours 9..16 (inclusive start, exclusive 17); NIGHT = 18..06 (as in master brief); RIDGE_LAMBDA = 5; ANOMALY_Z = 2.0; MIN_DAYS_FOR_PERSONAL_FIT = 5.
Tariff table (slabs, fuel/other charges, tax %) lives in `data/tariff.json` and is editable; never hard-code tariff numbers in code, and label every cost as an estimate.

## 6. Weather data
Open-Meteo (free, no key, non-commercial use) for forecast and archive. Check its current docs for endpoint names and variable names before coding (hourly temperature_2m, relative_humidity_2m, cloud_cover, shortwave_radiation; timezone=Asia/Karachi). Cache in `weather_cache`. If the call fails, fall back to the last cached day, then to a monthly climate normal table for the city; always tell the user which source was used. Home lat/lon come from `homes` (add a city picker with lat/lon for major Pakistani cities).

## 7. Definitions
CDH (cooling degree hours, per day) = sum over 24 h of max(0, temp_c[h] - COMFORT_SETPOINT_C).
Flexible load types: washing_machine, iron, water_pump, geyser (electric), vacuum_cleaner, electric_oven (not essential), ups charging (shiftable), water_dispenser (not shiftable). Fixed: refrigerator, deep_freezer, router, led_bulb, tube_light, tv. Comfort (weather-driven): ac, air_cooler, ceiling_fan, pedestal_fan.
Reference day: the average CDH of the 7 days before onboarding (from the archive endpoint); the user's stated hours are assumed to be for the reference day.

## 8. Working rules (same as master brief section 9)
One file at a time, exact paths, small edits only, plan in 6 bullets, HANDOFF NOTE at the end. Tests must run without the network (mock Open-Meteo with saved JSON fixtures).
