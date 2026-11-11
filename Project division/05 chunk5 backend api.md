Claude

















05 chunk5 backend api · MD
CHUNK 5 — Backend endpoints (homes, appliances, detect, catalog, sizing)
(Paste MASTER BRIEF first, then this card. Start AFTER chunks 1, 3 and 4 exist in the repo. In this chat, paste the files it must call: api/app/auth.py, api/app/db.py, api/app/config.py, the public function signatures from sizing.py, schedules.py, detect.py, catalog.py. Do not paste whole files unless needed.)

Goal
All HTTP routes from MASTER BRIEF section 7 for Part 1, wired to the database, the detection service and the sizing engine, with ownership checks and clean errors.

Files to write (one at a time)
api/app/schemas.py — EXTEND the file chunk 4 already created (keep DetectedItem unchanged) with ApplianceIn, ApplianceOut, HomeIn, HomeOut, FinalizeIn, SizeRequest, SizeResponse. Reuse LoadItem, SizingAssumptions, SizingResult from services/sizing.py. If the file does not exist yet, create it including DetectedItem from MASTER BRIEF section 6.
api/app/deps.py — get_owned_home(home_id, user) dependency: loads the home, returns 404 if missing, 403 if home.user_id != user.id. get_owned_appliance(appliance_id, user) similar through its home.
api/app/routers/homes.py — list/create/get/patch/delete homes (only the caller's homes).
api/app/routers/appliances.py — list, create, bulk create, patch, delete.
api/app/routers/detect.py — detect + finalize.
api/app/routers/catalog.py — search and types (public to logged-in users).
api/app/routers/sizing.py — size + reports list.
Update api/app/main.py to include the routers.
api/scripts/smoke_test.sh (curl commands) and api/tests/test_api_logic.py for logic that does not need a live database (helpers such as building LoadItems).
Behaviors that must be exactly right
Appliances

On create/bulk: if hourly_use is empty or not 24 long, build it with default_hourly_use(type, hours_per_day) where hours_per_day comes from the request (hours_per_day field, default from catalog default_hours). Store hourly_use always as 24 numbers.
Validate: qty 1..50, watts 0..20000, duty (0,1], surge >= 1, type in the allowed slugs (else 422).
PATCH sets user_verified=true and source_tag="user" for any field the user changed (watts, brand, model, capacity, qty, hours); keep confidence untouched. Update updated_at.
Bulk create accepts up to 40 items and inserts in one call.
Response includes hours_per_day (sum of hourly_use) for UI convenience.
Detect

POST /homes/{id}/detect: multipart with image (jpeg/png/webp, max 8 MB, else 413/415) and room (text).
Steps: verify home ownership -> upload the original (resized to max 1600 px by Pillow) to Storage bucket appliance-images at {user_id}/{home_id}/{uuid}.jpg -> call detect() -> insert a detections row (predicted = items as JSON, backend from env) -> return {detection_id, image_path, items}.
If detection fails, return 502 with {"error": "...friendly message..."} and still keep the uploaded image path out of the DB (delete the upload).
POST /detections/{id}/finalize body {final_items: [...]} stores the user's corrected list into detections.final. Only the owner may call it. Idempotent (overwrites).
Catalog

Load once at startup from the CSV (reuse services/catalog.py). GET /catalog/search?q=&type=&limit=10 returns rows with the fields needed to prefill an appliance form. GET /catalog/types returns types with default_hours, typical watts, and a label for the UI.
Sizing

POST /homes/{id}/size body {assumptions?: {...partial overrides...}}: load the home's appliances, convert to LoadItems (fill missing hourly_use with defaults), run size_system, insert into sizing_reports (input = items + assumptions, result), return {report_id, created_at, result}. With no appliances return 422 {"error": "Add at least one appliance first"}.
GET /homes/{id}/reports -> latest 20 reports (id, created_at, headline numbers).
Errors and safety

One error format: {"error": "message", "code": "SOME_CODE"}. Add an exception handler.
Never return another user's data. Never expose the service-role key or raw tracebacks.
Rate limit: simple in-memory limit of 10 detect calls per user per hour (protects the free AI quota). Return 429 with a friendly message.
Log request id, user id and duration; never log image bytes or tokens.
Smoke test script (smoke_test.sh)
Use curl with a token pasted into TOKEN=: create home, add an AC and a fan manually, list appliances, call size, upload a photo to detect, finalize. Print status codes.

Acceptance
 With two accounts, account B gets 403/404 on account A's home and appliances for every route.
 Creating an appliance without hourly_use stores a 24-length array.
 POST /size returns the same numbers as the worked example from chunk 3 when you enter the same four appliances.
 A 9 MB image is rejected cleanly; a non-image is rejected cleanly.
 Swagger docs (/docs) show every route with examples.
Handoff
HANDOFF NOTE: list of routes with one-line request/response examples (this is what chunk 6 needs), env vars added, and anything not implemented.


