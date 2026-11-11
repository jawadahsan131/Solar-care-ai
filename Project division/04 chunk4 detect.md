Claude

















04 chunk4 detect · MD
CHUNK 4 — Appliance detection service (vision-LLM now, YOLO later)
(Paste MASTER BRIEF first, then this card. Needs no other chunk's code, but at the end it will read data/catalog/appliance_catalog.csv from chunk 2; use a small fake catalog for tests until it exists.)

Goal
One function the backend calls: detect(image_bytes, mime) -> list[DetectedItem]. Today it is powered by a vision LLM (Gemini free tier). When the YOLO model is trained (chunk 8), a second backend plugs in with no other code change. The service must NEVER pretend to know capacity or watts it cannot see; it must say where each value came from.

Files to write (one at a time)
api/app/schemas.py — create it now with ONLY the DetectedItem model exactly as in MASTER BRIEF section 6 (chunk 5 will extend this file later and must keep DetectedItem unchanged).
api/app/services/catalog.py — loads the CSV once, search and matching helpers.
api/app/services/detect_vlm.py — vision-LLM backend.
api/app/services/detect_yolo.py — stub with the same interface (raises NotImplementedError with a clear message; chunk 8 fills it).
api/app/services/detect.py — router: picks backend from env DETECT_BACKEND (vlm default | yolo), runs post-processing, returns DetectedItem list.
api/scripts/test_detect.py — command line: python scripts/test_detect.py photo.jpg prints a readable table.
api/tests/test_detect_postprocess.py — tests for post-processing without calling the network.
catalog.py
load_catalog(path) -> list of rows (lowercase types, floats parsed, blanks -> None). Path from env CATALOG_PATH default data/catalog/appliance_catalog.csv; if the file is missing, log a warning and use a built-in minimal fallback (ac 1.5 ton 1700 W; fan 75 W; fridge 150 W duty 0.4; tv 60 W; bulb 12 W; washing machine 400 W).
match(type, brand, model, capacity_value, capacity_unit, inverter) -> (row, level) where level is exact (brand+model match, use rapidfuzz ratio >= 90 on normalized text), brand_capacity, type_capacity, type_only, or none. Capacity matching tolerance: within 10 percent.
search(q, type, limit) for the autocomplete endpoint (rapidfuzz over "brand model type capacity").
types_info() -> list of {type, default_hours, typical_watts} for the UI.
detect_vlm.py (Gemini free tier)
Use the official Google GenAI Python SDK; model name from env GEMINI_MODEL (check Google's current docs for a Flash model name; do not hardcode), key from GEMINI_API_KEY.
Resize first with Pillow: longest side 1280 px, JPEG quality 85, fix EXIF rotation.
Ask for STRUCTURED JSON (response schema), a list of objects: type (must be one of the allowed slugs else "other"), brand, model, capacity_text (exactly as visible, e.g. "1.5 Ton", "18000 BTU", "56 inch", "12 cu ft"), inverter_text (visible words like "Inverter"/"DC Inverter" or null), rated_power_text (exactly as printed on a label, e.g. "1650W", "1.2 kW", or null), label_text (all label text you could read), count (how many identical units are clearly visible), confidence (0..1, honest), notes.
Prompt skeleton to adapt: "You are inspecting a photo taken inside a home in Pakistan. List every ELECTRICAL APPLIANCE that is clearly visible. For each one return the fields in the schema. Rules: (1) Only report brand, model, capacity, inverter, or power if you can actually READ it in the image (logo, sticker, rating plate). Otherwise use null. Never guess a brand or a wattage. (2) Copy visible label text exactly into label_text. (3) If several identical units are visible, return one object with count. (4) Ignore non-electrical objects, people and furniture. (5) If unsure of the type, use type 'other' and explain in notes. (6) Confidence reflects how sure you are of the TYPE and any text you read."
Timeout 30 s, one retry, then raise a clean DetectionError. Catch quota errors (HTTP 429) and raise DetectionError("Detection service is busy, please try again or add items manually").
Never log image bytes. Do not store the key in code.
Post-processing (detect.py) — the important part
For each raw VLM object:

Normalize: type in allowed slugs else "other"; parse capacity_text into (value, unit) (ton, btu -> convert to ton = btu/12000, inch, litre, kg, cu_ft, hp); parse rated_power_text to watts (W, kW, "VA" -> treat as watts with a note); inverter = true if text contains "inverter", else null.
Match to catalog with match(...).
Decide values and tags:
watts printed on a label -> watts = that value, source_tag="label", confidence = min(0.95, model_confidence + 0.1).
else catalog exact -> source_tag="catalog", confidence = min(0.85, model_confidence).
else catalog brand_capacity / type_capacity -> source_tag="guess", confidence = min(0.6, model_confidence).
else type_only / none -> source_tag="guess", confidence = min(0.4, model_confidence), notes "typical value, please confirm".
copy duty_factor, surge_factor, default_hours from the matched row (or type defaults).
If inverter is unknown for an AC, leave inverter=None and add notes "inverter or not? please confirm" (the UI will ask the user).
count -> carried through (qty).
Sort by confidence descending. Return DetectedItem objects exactly as defined in MASTER BRIEF section 6.
Tests (no network)
Feed hand-written raw JSON into the post-processor and check: label watts wins; BTU 18000 becomes 1.5 ton; unknown brand gives guess and low confidence; type not in slug list becomes "other"; duplicate-free output; capacity tolerance matching.
Test that a missing catalog file triggers the fallback instead of crashing.
Acceptance
 python scripts/test_detect.py room.jpg prints items with source tags for a real photo (AC outdoor unit with a rating plate, a fan, a fridge). Try at least 5 real photos from your phone.
 A photo with no appliances returns an empty list, not an error.
 Swapping DETECT_BACKEND=yolo raises the clear "not implemented yet" error.
Privacy note to show in the app
Images are sent to a third-party AI service for analysis. Free-tier terms may allow the provider to use submitted data to improve its products (check the provider's current terms). Add a consent line before the first upload and delete raw images after processing unless the user opts in.

Handoff
HANDOFF NOTE: env vars needed, model name used, parsing limitations you noticed, 3 failure cases from your test photos.


