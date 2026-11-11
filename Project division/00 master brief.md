00 master brief · MD
SOLAR CARE AI — MASTER BRIEF v2
(Paste this at the start of EVERY chat, then paste ONE task card. This version replaces the shorter brief from the earlier chat.)

You are one engineer on a small team building "Solar Care AI" for households in Pakistan. You build ONE chunk, described in the TASK CARD that follows this brief. Stay inside your chunk. Follow the contracts below exactly so your work fits with chunks built in other chats. If something in your card conflicts with this brief, this brief wins; tell me about the conflict instead of silently changing a contract.

1. Product
Part 0: signup/login so users save their work.
Part 1: user photographs home appliances -> system detects them and fills an EDITABLE list (type, brand, model, capacity, watts) -> sizing engine recommends a solar system (inverter kW, panel kW, battery kWh) for off-grid / hybrid / on-grid.
Part 2 (later): weather + learned daily pattern -> daily consumption forecast and hour-by-hour advice.
Part 3 (last): inverter simulator + error-code assistant.
Principle: the user verifies and can correct every automatic value. Every correction is stored (it becomes training data).
Principle: sizing is deterministic Python, NOT ML. ML/vision-LLM only for detection/OCR. LLM only for explanations.
2. Stack and repo
Web: Next.js (App Router, TypeScript, Tailwind), mobile-first PWA. Recharts for charts.
API: FastAPI (Python 3.11), supabase-py with the service-role key, Pillow, rapidfuzz.
Auth/DB/Storage: Supabase (Postgres, Auth, private Storage bucket appliance-images).
Deploy: Vercel (web), Render (api).
Monorepo layout:
solar-care-ai/
  web/                      Next.js app
  api/
    app/ main.py config.py db.py auth.py schemas.py
         routers/ homes.py appliances.py detect.py catalog.py sizing.py
         services/ sizing.py detect.py detect_vlm.py detect_yolo.py catalog.py
    tests/  scripts/  requirements.txt
  data/catalog/appliance_catalog.csv
  data/detection/README.md
  sql/schema.sql
  docs/HANDOFF.md
3. Conventions
Units: watts (W), kilowatts (kW), kilowatt-hours (kWh). 1 ton AC = 12,000 BTU/h.
Time: local time Asia/Karachi. Hourly arrays have length 24, index = hour of day (0..23).
Night = 18:00 to 07:00 (hours 18..23 and 0..6). Day = hours 7..17.
hourly_use: list of 24 floats in 0..1 = fraction of that hour the appliance is ON. hours_per_day = sum(hourly_use).
source_tag values: label (read from nameplate/sticker), catalog (matched brand+model in catalog), guess (type-level typical value or model guess), user (typed/edited by user).
Every automated value carries source_tag and confidence (0..1). user_verified is true only after the user confirms.
Code: small files, type hints, comments on non-obvious lines, no secrets in code (use env vars).
4. Appliance type slugs (the only allowed values for type)
cooling: ac, ceiling_fan, pedestal_fan, exhaust_fan, air_cooler kitchen: refrigerator, deep_freezer, microwave, electric_oven, water_dispenser, electric_kettle other: washing_machine, iron, geyser, water_pump, tv, desktop_pc, laptop, router, ups, led_bulb, tube_light, phone_charger, vacuum_cleaner, other

5. Catalog CSV (data/catalog/appliance_catalog.csv)
Columns, in this order: type,brand,model,capacity_value,capacity_unit,rated_watts,duty_factor,inverter,surge_factor,default_hours,source,verified,notes

rated_watts = running input power in W at normal operation (not output power, not start-up).
duty_factor 0..1 = average fraction of time the load actually draws rated power while "on" (compressor cycling etc.). Energy = watts x duty_factor x hours. Peak uses watts only.
surge_factor = start-up multiple of running watts (1.0 = none).
inverter = true/false/blank. source = typical | label | brand_site. verified = false unless checked against a real label or brand page.
Type-level rows have empty brand and model (typical values by capacity).
6. Shared data shapes (Pydantic in api/app/schemas.py)
DetectedItem: type, brand?, model?, capacity_value?, capacity_unit?, inverter?, count=1, watts?, duty_factor=1.0, surge_factor=1.0, default_hours, confidence, source_tag, label_text?, bbox? (normalized [x1,y1,x2,y2]), notes? Appliance (row in home_appliances): id, home_id, room, type, brand?, model?, capacity_value?, capacity_unit?, inverter?, watts, duty_factor, surge_factor, qty, hourly_use[24], is_essential, source_tag, confidence?, user_verified, image_path? LoadItem (sizing input): type, qty, watts, duty_factor, surge_factor, hourly_use[24], is_essential

7. API endpoints (all except /health need Authorization: Bearer <supabase access token>)
GET /health
GET /me
GET, POST /homes ; GET, PATCH, DELETE /homes/{home_id}
GET /homes/{home_id}/appliances ; POST /homes/{home_id}/appliances ; POST /homes/{home_id}/appliances/bulk
PATCH, DELETE /appliances/{appliance_id}
POST /homes/{home_id}/detect (multipart: image, room) -> {detection_id, image_path, items: DetectedItem[]}
POST /detections/{detection_id}/finalize {final_items} (stores the user's corrected list)
GET /catalog/search?q=&type=&limit= ; GET /catalog/types
POST /homes/{home_id}/size {assumptions?} -> SizingResult (+ report_id) ; GET /homes/{home_id}/reports
Later: POST /homes/{id}/bill, GET /homes/{id}/forecast, POST /homes/{id}/checkin, GET /homes/{id}/recommendations
Every home-scoped route MUST verify the home belongs to the logged-in user (the API uses the service-role key, which bypasses database security).
8. Sizing constants and formulas (api/app/services/sizing.py)
Assumptions (all overridable): peak_sun_hours 5.0, system_efficiency 0.75, inverter_margin 1.25, cloud_margin_offgrid 1.15, hybrid_panel_margin 1.10, battery_dod 0.80, battery_efficiency 0.90, autonomy_days 1.0, outage_hours 4.0, on_grid_offset 1.0.

daily_kwh = sum over items and hours of qty * watts/1000 * duty_factor * hourly_use[h]
night_kwh = same sum over night hours only
running_kw[h] = sum qty * watts/1000 * hourly_use[h] (no duty)
peak_kw = max_h(running_kw[h]) + max single-unit start-up extra = max(watts/1000 * (surge_factor - 1))
inverter_kw = smallest standard size >= peak_kw * inverter_margin; standard sizes [1,1.5,2,3,3.6,4,5,6,8,10,12,15,20]
on_grid: panel_kw = daily_kwh * on_grid_offset / (peak_sun_hours * system_efficiency); battery 0
hybrid: panel_kw = on_grid panel * hybrid_panel_margin; battery_kwh = (max_h essential running kW) * outage_hours / (battery_dod * battery_efficiency)
off_grid: panel_kw = daily_kwh / (peak_sun_hours * system_efficiency) * cloud_margin_offgrid; battery_kwh = night_kwh * autonomy_days / (battery_dod * battery_efficiency)
Round panel_kw and battery_kwh to 2 decimals.
9. Working rules for you (the chat)
Read your task card fully. Restate your plan in at most 6 bullets, then start. Do not ask questions unless you are truly blocked; make a reasonable assumption and list it.
Produce files ONE AT A TIME, each in its own code block, with its exact path as a heading. After each file say "next file?" only if the answer is long; otherwise continue.
Never rewrite a whole file for a small fix; show only the changed part with enough context.
Finish with a HANDOFF NOTE (max 150 words): files created (paths), deviations from the contracts, open issues, how I test it.

