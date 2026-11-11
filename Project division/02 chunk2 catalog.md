Claude

















02 chunk2 catalog · MD
CHUNK 2 — Appliance spec catalog (three separate chats: 2a, 2b, 2c)
(Paste MASTER BRIEF first, then ONLY your section below: 2a cooling, 2b kitchen, 2c other.)

Why this matters
The catalog is the most valuable asset in Part 1. The vision model only says "this is an AC". The catalog says what watts, duty and start-up surge a 1.5 ton inverter AC really has. It must be honest: values are "typical" until verified against a real nameplate.

Common rules (all three sections)
Output a CSV with EXACTLY these columns, in this order, with a header row: type,brand,model,capacity_value,capacity_unit,rated_watts,duty_factor,inverter,surge_factor,default_hours,source,verified,notes
Give 30-45 rows. Output in code blocks of at most 25 rows each so nothing is cut off.
Two kinds of rows:
TYPE-LEVEL rows: brand and model empty, one row per capacity/variant (this is the fallback, the most important rows).
BRAND rows: only for brands and models you are confident exist in Pakistan. If unsure, do not invent a model name; use a type-level row instead. Brand rows start with the same typical numbers unless you know the real label values.
source = typical for anything not read from a real label or brand page. verified = false always (the human will verify later). Put in notes what the human must check ("check rating plate").
Do NOT invent precise watt values and present them as certain. Stay inside the reference ranges below; they are approximate and may be adjusted after real labels are checked.
Capacity units: ac=ton, fans=inch, air_cooler=litre, refrigerator/deep_freezer=cu_ft, microwave=litre, washing_machine=kg, geyser=litre, water_pump=hp, tv=inch, ups=va, others blank.
default_hours = typical hours per day in a Pakistani home (summer unless stated); the user edits it later.
At the end add a short "Please verify first" list: the 10 rows the human should check on real labels first.
2a — COOLING (types: ac, ceiling_fan, pedestal_fan, exhaust_fan, air_cooler)
Reference ranges (approximate; adjust only if you have good reason):

ac non-inverter: 1 ton 1000-1200 W, 1.5 ton 1600-1800 W, 2 ton 2200-2500 W; duty 0.60-0.70; surge 4-5; default_hours 8.
ac inverter (DC inverter): 1 ton 800-1000 W, 1.5 ton 1200-1500 W, 2 ton 1800-2100 W (maximum running input); duty 0.45-0.60 (average load is well below maximum); surge 1.5-2.0; default_hours 8.
Include capacities 0.75, 1, 1.5, 2 ton, and 3 and 4 ton (cassette/floor-standing) for type-level rows. Both inverter true and false.
ceiling_fan AC motor 56 inch 70-90 W; 48 inch 60-75 W; DC/inverter fan 28-40 W (inverter true); duty 1.0; surge 1.3; default_hours 10.
pedestal_fan 16-18 inch 55-80 W; surge 1.3; default_hours 6. exhaust_fan 8-12 inch 25-70 W; default_hours 2.
air_cooler (room evaporative, Pakistan) 150-250 W; duty 1.0; surge 2; default_hours 8.
Brands to consider for brand rows (only if confident): Haier, Gree, Dawlance, Orient, PEL, Kenwood, TCL, Midea, Changhong Ruba (AC); Pak Fan, GFC, Royal, Signature, Asia, Super Asia, Millat (fans and coolers).
2b — KITCHEN (types: refrigerator, deep_freezer, microwave, electric_oven, water_dispenser, electric_kettle)
Reference ranges:

refrigerator conventional 9-12 cu ft 100-150 W; 14-18 cu ft 130-200 W; 20+ cu ft 180-260 W; duty 0.35-0.45; surge 3-4; default_hours 24. Inverter fridges 15-25% lower, duty 0.30-0.40, surge 1.5-2.
deep_freezer 150-300 W; duty 0.45-0.55; surge 4; default_hours 24.
microwave 20-30 litre: 1000-1500 W input; duty 1.0; surge 1.2; default_hours 0.3.
electric_oven (toaster/bake) 1200-2200 W; duty 0.7; default_hours 0.5.
water_dispenser hot+cold 450-600 W; duty 0.25-0.35; surge 3; default_hours 24.
electric_kettle 1500-2200 W; duty 1.0; default_hours 0.3.
Brands to consider (only if confident): Dawlance, Haier, PEL, Orient, Samsung, LG, Kenwood, Nasgas (dispensers), Super Asia, Anex, West Point, National (small appliances).
2c — OTHER (types: washing_machine, iron, geyser, water_pump, tv, desktop_pc, laptop, router, ups, led_bulb, tube_light, phone_charger, vacuum_cleaner, other)
Reference ranges:

washing_machine semi-automatic twin tub 7-10 kg 250-450 W; fully automatic 7-10 kg 350-600 W; surge 2.5-3; default_hours 1.
iron 1000-1600 W; duty 0.7; default_hours 0.5. vacuum_cleaner 800-1600 W; default_hours 0.3.
geyser electric storage 35-60 litre 1500-3000 W, duty 0.4, default_hours 2 (note: many homes use gas geysers, put this in notes; default 0 in summer).
water_pump (motor) 0.5 hp about 450-600 W, 0.75 hp 650-850 W, 1 hp 900-1150 W, 1.5 hp 1300-1700 W; surge 3-5; default_hours 1.
tv LED 32 inch 40-60 W, 43 inch 60-90 W, 50-55 inch 90-140 W, 65 inch 130-200 W; default_hours 5.
desktop_pc 150-350 W, default_hours 5; laptop 40-90 W incl. charger, default_hours 6; router 8-15 W, default_hours 24.
ups 600-1500 VA standby/charging 30-150 W, duty 1.0, default_hours 24 (note: includes battery charging).
led_bulb 9-18 W (capacity_unit watt), tube_light LED 18-40 W / old 40 W, default_hours 6. phone_charger 5-20 W, default_hours 3.
Add a type other row: generic 100 W, hours 2, note "user must edit".
Brands to consider (only if confident): Dawlance, Haier, Super Asia, PEL, Boss, Gaba National (washers); Philips, Osram, Pak Electron (bulbs); Homage, Tesla, Phoenix (UPS).
After you get the three CSVs
YOU merge them into one file: data/catalog/appliance_catalog.csv (one header row only).
Check: every type is from the allowed slug list; no blank rated_watts; duty_factor in 0..1; surge_factor >= 1.
Verification pass (do it later, not today): photograph real nameplates at home or in shops and update rated_watts, source=label, verified=true for those rows.
Handoff
End with a HANDOFF NOTE (number of rows, rows you are least sure about, anything the human must verify).


