# CHUNK 11 — Daily check-in and weather-aware demand model (the core of Part 2)
(Paste MASTER BRIEF + PART 2 ADDENDUM, then this card. Needs: chunk 3 sizing items, chunk 10 `weather.py`/`solar.py` (or their signatures), and the `daily_logs` migration. Optional: calibration from chunk 9.)

## Goal
Learn each home's normal pattern from a few days of taps, predict the next day's consumption hour by hour from weather, and say whether a day was normal. Simple, explainable, honest about uncertainty. NOT a neural network.

## Files (one at a time)
1. `api/app/services/demand.py` — model (pure functions + one fit function).
2. `api/app/services/anomaly.py` — normal/high/low verdicts and reasons.
3. `api/app/routers/checkin.py` — check-in, demand, verdicts endpoints.
4. `scripts/make_synthetic.py` — synthetic homes with weather for testing (source="synthetic", clearly labelled, never mixed into real evaluation).
5. `api/tests/test_demand.py`, `api/tests/test_anomaly.py`, `api/tests/test_synthetic_recovery.py`.
6. Web: `/homes/[id]/checkin` (20-second form), `/homes/[id]/today` (prediction + verdict).

## Data model (what a check-in is)
Tap-only, pre-filled from yesterday: "Same as usual?" (one big yes button that saves the usual), AC hours today (stepper 0-24), outage hours, guests (yes/no), optional meter reading in kWh (an extra "photo of meter" can come later), optional per-appliance hours (expandable "something different today"). Saves to `daily_logs` (upsert by date). Backfill: allow past 7 days.

## Model (demand.py): physics-informed, per appliance type
For a given day with hourly weather:
1. **Base energy per appliance** = qty x watts/1000 x duty x hours_per_day (from the verified list; hours from the user).
2. **Weather factor per class** (relative to the reference day CDH_ref, addendum section 7):
   - ac, air_cooler: `f = clamp(CDH_day / CDH_ref, min, max)` with DEMAND_FACTOR_MIN/MAX. If CDH_ref is about 0 (cool season) use an absolute baseline: hours = base_hours_cool_season (default 0) + k x CDH_day / 10.
   - ceiling_fan, pedestal_fan: `f = clamp(0.3 + 0.7 x CDH_day/CDH_ref, FAN_MIN_FACTOR, 1.5)`.
   - geyser (electric): inverse with heating degree hours; refrigerator: `1 + 0.015 x (mean_temp - 25)` clamped 0.9..1.2; everything else f = 1.
3. **Hourly shape**: take the user's `hourly_use` and, for weather-driven classes, blend 50/50 with a weather weight w[h] proportional to max(0, T_h - setpoint). Renormalize so the daily hours equal base hours x f. Fixed classes keep their own schedule.
4. **Day-type effects** from check-ins: guests -> +10 percent on lights/fans/TV (editable); user-entered `ac_hours` replaces the AC hours; outage hours zero out the grid-fed loads in those hours (record as "unserved", used by the battery advice later).
5. **Personal fit** (only when n_days >= MIN_DAYS_FOR_PERSONAL_FIT and meter_kwh exists): per-home scale factors s_ac (comfort) and s_other solved by ridge regression toward 1: minimize sum (meter_kwh_d - (fixed_d x s_other + comfort_d x s_ac))^2 + RIDGE_LAMBDA x ((s_ac-1)^2 + (s_other-1)^2). Closed form, numpy only. Clamp scales to 0.5..2.0. Store in `demand_models.params`.
   Without meter data, use the bill ratio from chunk 9 as a single global scale. Without both, use priors (scale 1) and say so ("low confidence: no real readings yet").
6. **Uncertainty**: low/high = prediction +- 1.28 x residual std (80 percent band); before enough data use +-25 percent and confidence "low". Confidence: low (<5 days) / medium (5-14) / high (>14 and recent error < 15 percent).
7. **Drivers list** (explainability): e.g. "Hot day: 41 C max, cooling load +22 percent vs your usual", "Guests expected", "Cooler than usual".

## Anomaly (anomaly.py)
Residual = actual - expected (expected computed with that day's real weather and check-in context, not the plain average). z = residual / robust std (MAD x 1.4826, floor at 10 percent of expected). Status: high if z > ANOMALY_Z, low if z < -ANOMALY_Z, else normal; unknown if fewer than 5 days. Reasons ranked: AC hours above expected; appliance hours the user reported; meter vs list mismatch; "possible unlisted appliance". NEVER say "fault" or accuse; say "higher than expected for this weather: check these".

## Endpoints
`POST /homes/{id}/checkin`, `GET /homes/{id}/checkins?days=30`, `GET /homes/{id}/demand?date=` (DemandPrediction), `GET /homes/{id}/verdicts?days=14` (DayVerdict list). Refit the model automatically after each check-in that includes `meter_kwh` (cheap, closed form).

## Synthetic data (to test BEFORE real users have 7 days)
`make_synthetic.py`: create a home with 8 appliances, 40 days of weather from the archive endpoint (or fixture), generate "true" daily kWh with a hidden AC scale and noise (5-8 percent), inject 3 abnormal days (+40 percent), write check-ins with `source="synthetic"`. The test must show: the fitted scale recovers the hidden one within 15 percent after 14 days, the three abnormal days are flagged, and prediction error beats a naive "average of past days" baseline on hot/cool days. Mark all synthetic rows so they are excluded from the real evaluation and the demo says so.

## Web
- Check-in page: big "Same as usual" button, AC stepper, outages, guests, optional meter number. Streak of days logged.
- Today page: predicted kWh with range, hourly chart (predicted load; actual if logged), drivers as short sentences, verdict badge for yesterday, confidence label ("learning: 3 of 7 days").

## Acceptance
- [ ] A new home with no data still gets a prediction (priors) labelled low confidence.
- [ ] After 7 real or synthetic days the confidence and band change on screen.
- [ ] Synthetic tests pass (recovery, anomaly flags, beats naive baseline).
- [ ] All numbers can be explained in one sentence each (drivers list).

## Handoff
HANDOFF NOTE: parameters chosen, files, what the model cannot do (per-appliance disaggregation, unusual appliances), test results.
