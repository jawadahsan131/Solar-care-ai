# CHUNK 9 — Electricity bill reading and calibration
(Paste MASTER BRIEF + PART 2 ADDENDUM, then this card. Needs Part 1 in the repo: paste `sizing.py` signatures, `detect_vlm.py` (to reuse its image helpers and error style), and `schemas.py`.)

## Why
The appliance list is an estimate. The bill is real data. Comparing them is the cheapest accuracy upgrade in the project and it also gives the seasonal pattern (summer vs winter units).

## Files (one at a time)
1. `api/app/services/bill_ocr.py` — reads a bill photo with the same vision-LLM provider as detection, returns structured fields.
2. `api/app/services/calibration.py` — pure functions, no network or database.
3. `api/app/routers/bills.py` — endpoints.
4. `api/tests/test_calibration.py`, `api/tests/test_bill_ocr_parse.py`.
5. Web: `/homes/[id]/bills` page + a card on the Report page.

## bill_ocr.py
- Input: image bytes. Output: `{units_kwh?, month?, history: [{month, units}], amount_pkr?, disco?, confidence, raw_text}`. Pakistani bills differ by company (LESCO, K-Electric, IESCO, etc.) and layouts change, so the model must return null for anything it cannot read. Never guess a number.
- Ask for structured JSON: current month units consumed, billing month, the monthly history table if present (month + units), total amount, company name. Parse months like "OCT 25" or "10/2025" into the first day of that month.
- Validate: units between 0 and 5000, months not in the future; drop impossible rows with a warning.
- Same safety as detection: resize, 30 s timeout, friendly error, no image bytes in logs, rate limit shared with detect.
- ALWAYS show the parsed values in an editable form; the user confirms before saving to `bills`.
- If OCR fails, manual entry form: month + units (always available, it is the fallback and the main path on a bad day).

## calibration.py (pure functions)
- `estimate_monthly_kwh(items, month_factor)` from the sizing items; `month_factor` is a seasonal multiplier for weather-driven loads (default 1.0; Part 2 weather model refines it later).
- `calibration_ratio(bill_units, estimated_units)` = bill / estimate. Compute per bill, then a robust overall ratio (median of the last 3 months, or the single value).
- Verdict bands: within 15 percent = "good match"; 15-30 percent = "check hours/quantities"; beyond 30 percent = "estimate is far from your bill". Give the most likely reasons: missed appliances, hours too low/high, AC usage differences, the bill includes other charges (units only, not amount).
- `suggest_scaling(items, ratio)` returns a PROPOSAL, never auto-applies: scale weather-driven loads (comfort type) first, then flexible loads, never fridge/lights. The user accepts or rejects it on screen ("Increase AC hours from 8 to 10?").
- Seasonality: if 6+ months of history exist, compute a monthly index (month units / average) and store it in `calibration` for the weather model to use in chunk 11.

## Endpoints
- `POST /homes/{id}/bill` multipart image -> parsed values (NOT saved yet); `POST /homes/{id}/bills` JSON `{month, units_kwh}` saves (upsert on month). `GET /homes/{id}/bills`. `GET /homes/{id}/calibration` -> `{estimated_monthly_kwh, bill_monthly_kwh, ratio, band, reasons[], proposals[], monthly_index?}`.
- `DELETE /bills/{id}` with ownership check.

## Web
- Bills page: upload photo or enter manually, review/edit screen, list of saved months, small bar chart of units per month.
- Report page card: "Your appliance list estimates X kWh/month, your bill says Y. Match: good / check". Button "Review suggestions" shows proposals as accept/reject toggles that then PATCH the appliances (marking them user-verified).

## Tests (no network)
- Ratio and band boundaries; proposals never touch fridge/lights; month parsing ("OCT 25", "10/2025", "Oct-2025"); impossible values dropped; estimate monthly = daily x 30 with the seasonal factor.

## Acceptance
- [ ] Photo of a real bill from a friend (blur personal details like name and address before uploading to anything) gives units and month, or fails gracefully to manual entry.
- [ ] Manual entry of 3 months produces a calibration card.
- [ ] Applying a proposal updates the list and the report numbers change.
- [ ] Privacy note shown: bill images go to a third-party AI; the app stores only month and units, deletes the image after parsing.

## Handoff
HANDOFF NOTE with the bill formats you tried and what failed.
