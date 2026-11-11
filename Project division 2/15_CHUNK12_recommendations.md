# CHUNK 12 — Hour-by-hour recommendations and dashboard
(Paste MASTER BRIEF + PART 2 ADDENDUM, then this card. Needs chunks 10 and 11 (forecast and demand). A system size is needed: use `homes.system_kw` if set, else the panel_kw of the latest sizing report option the user chose.)

## Goal
Turn forecast + predicted demand into a few concrete, numeric, believable actions: "Run the washing machine at 12:00 instead of 21:00, saves about 0.6 kWh of grid/battery use". The optimizer decides; text is only wording.

## Files (one at a time)
1. `api/app/services/recommend.py` — optimizer (pure functions).
2. `api/app/services/tariff.py` — cost estimate from `data/tariff.json` (editable slabs, never hard-coded).
3. `api/app/routers/recommendations.py`.
4. `data/tariff.json` — a sample structure with clearly marked placeholder numbers the human must update from the current official tariff.
5. `api/tests/test_recommend.py`.
6. Web: `/homes/[id]/plan` (today's plan) and a combined dashboard `/homes/[id]/dashboard`.

## Model of the day
- `solar_kw[h] = pv_kw_per_kwp[h] x system_kw` (from chunk 10). `load_kw[h]` from the DemandPrediction (chunk 11).
- Direct use `min(solar, load)`, surplus `max(0, solar - load)` (exported or stored), deficit `max(0, load - solar)` (battery/grid).
- Metrics: self-consumption %, solar coverage %, evening/night deficit kWh, estimated grid import kWh (with and without the plan).
- If the home has no solar yet (pre-purchase), run the same computation with the planned system to produce a "what your day would look like" chart.

## Optimizer (greedy, explainable)
1. Only flexible appliances (addendum section 7) that are in the list and used today. Each has `hours_needed` (a contiguous block for washing machine, iron, vacuum; splittable for pump and geyser) and a user-allowed window (default 8:00-20:00; user can set quiet hours and "not possible" windows).
2. For each flexible load, find the placement inside its allowed window that maximizes `sum over its hours of min(load_kw_added, solar_surplus[h])` (use remaining surplus after earlier placements). Process larger loads first.
3. Accept a move only if it saves at least 0.2 kWh of non-solar energy or 10 percent of that load's energy. Keep at most 5 recommendations, ordered by saving. Each has `kwh_moved`, `grid_import_saved_kwh`, `difficulty` (easy = timer-capable, hard = requires someone at home), and a rule-based `reason`.
4. Comfort loads: never recommend turning off AC for health reasons. Offer soft tips instead: pre-cool in the solar window (set the AC 1-2 C lower between 11:00 and 15:00 and relax later) shown with an estimated effect, labelled "experimental".
5. Battery-aware tip (when `battery_kwh` known): if the evening deficit exceeds usable battery, say how many kWh must come from the grid and which loads to avoid in that period.
6. Cloud and soiling: when cloud_cover is high or a dust day, widen the margin and say so ("tomorrow is cloudy: plan lighter").
7. Outage awareness: if outage hours were reported, keep essential loads only in those hours and show unserved energy.

## Cost
`tariff.py` estimates bill impact from kWh moved/saved using slab structure with a clear "estimate, tariff updated on <date>" label. If no tariff file is valid, show kWh only.

## Endpoints
`GET /homes/{id}/recommendations?date=` -> `{day, metrics, solar_kw[24], load_kw[24], plan_load_kw[24], recommendations[]}`; `POST /homes/{id}/recommendations/{rec_id}/feedback` (done | skipped | not_possible). Feedback tunes the next day: a loads marked "not_possible" in a window gets that window excluded; log it for the evaluation.

## Web
- Plan page: a chart with three lines (solar, current load, planned load), a coloured band for the solar window, then the 3-5 recommendation cards with Done / Not possible buttons. A sentence at the top with the day summary ("Sunny, 6.2 sun hours; you can run about 4.1 kWh directly from solar").
- Dashboard: tiles for predicted kWh, solar coverage %, self-consumption %, verdict for yesterday, and the plan summary. Tables and chart on a phone must not scroll horizontally.

## Tests
- Surplus placement chooses the sunniest window; respects quiet hours; never exceeds 5 recommendations; does nothing when there is no surplus; no recommendation for fridge or lights; battery-aware text appears only when battery known; numbers add up (plan total energy equals current total energy, only the timing changes).

## Acceptance
- [ ] With a demo home (8 appliances, 3 kWp) the plan shows 2-4 sensible moves and the plan load line differs from the current load only in timing.
- [ ] Total energy before and after the plan is identical (test).
- [ ] Wording is cautious: "estimate", "if possible", no safety-critical advice.

## Handoff
HANDOFF NOTE: optimizer parameters, tariff file status, known limits.
