# CHUNK 13 — What-if simulator, PDF report and evaluation
(Paste MASTER BRIEF + PART 2 ADDENDUM, then this card. Run after chunks 10-12 work. Split into three small chats: 13a what-if, 13b PDF report, 13c evaluation.)

## 13a — What-if simulator (pre-purchase decision tool)
- Endpoint `POST /homes/{id}/whatif {panel_kw, battery_kwh?, inverter_kw?, outage_hours?}` -> typical-year summary.
- Method: simulate 12 representative days (one per month, from climate normals or archive averages) using the same solar and demand functions as chunks 10-11; sum to a yearly estimate. Output: yearly solar kWh, share of load covered by solar, self-consumption %, grid import avoided, estimated yearly bill saving using `data/tariff.json`, simple payback range with a cost input the USER enters (cost per kW is an input field with a placeholder, never a hidden number), battery effect (evening coverage), outage coverage hours.
- Compare 3 scenarios on one screen (e.g. 3 kW no battery, 5 kW hybrid with 5 kWh, 8 kW off-grid). Include a plain statement: "estimates, not a quotation".
- Sensitivity: a low/base/high band (sun -10 percent, demand +/-15 percent).
- Web: sliders for panel kW and battery kWh, three result cards, chart of average day (solar vs load) per season. Tests: monotonic (bigger system never covers less), battery only helps in the evening, edge case panel_kw = 0.

## 13b — PDF report (one page, for the user and the teacher)
- Browser print stylesheet first (works with no new code); then optional server PDF with WeasyPrint or a headless-browser export if time remains.
- Contents: home name/city/date, appliance table with source badges and a "verified" mark, daily kWh and peak, three system options, calibration vs bill (if available), key assumptions, warnings, disclaimer ("planning estimate, confirm with a qualified installer"), a footer with the report id and the date.
- Test: opening the print view with a sample home produces one A4 page (two if the appliance list is long).

## 13c — Evaluation (this is what turns a demo into a project)
Create `docs/evaluation.md` and `scripts/evaluate.py`.
**Part 1 metrics** (on real photos with real final lists):
- Detection: type accuracy and per-class precision/recall on at least 100 labelled photos (the user's final list is the ground truth from `detections.final`).
- Edit effort: percent of items the user had to change (type, capacity, qty, watts), seconds to complete a list, percent of values by source tag (label/catalog/guess/user).
- Sizing sanity: estimated monthly kWh vs real bills for N homes (MAPE) and the share within 15 percent.
**Part 2 metrics**:
- Daily kWh prediction error (MAPE and MAE) vs two baselines: (a) yesterday, (b) average of past 7 days. Use time-ordered evaluation (train on days before, predict the next day), never random splits.
- Anomaly: precision/recall on injected abnormal days (synthetic) and agreement with user feedback on real days.
- Recommendations: percent marked done, estimated kWh moved per day, user rating (1-5) of usefulness.
**User study** (minimum viable): 5-10 households, 7+ days, one short feedback form (usefulness 1-5, trust 1-5, what was confusing, would you use it before buying solar). Report results in a table with the sample size stated honestly.
**Honest limits section**: synthetic data labelled as synthetic; small sample; catalog values partly typical; weather forecast errors; no per-appliance metering.
Deliver: `docs/evaluation.md` with tables, a results chart per metric (inline images saved to `docs/figs/`), and 5 failure cases with screenshots and what was changed because of them.

## Acceptance
- [ ] What-if works for three scenarios and numbers move in the expected direction.
- [ ] A one-page PDF of a demo home can be saved from the browser.
- [ ] `evaluate.py` runs end to end on synthetic + whatever real data exists and writes the tables.

## Handoff
HANDOFF NOTE: metrics obtained so far, sample sizes, gaps.
