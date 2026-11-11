Claude

















07 chunk7 integration deploy · MD
CHUNK 7 — Integration, testing and deployment (evening)
(Paste MASTER BRIEF first, then this card. Run it when chunks 1, 3, 4, 5, 6 are in the repo. Bring the contents of docs/HANDOFF.md and any error messages. Keep this chat short and focused: one bug at a time.)

Goal
The full Part 0 + Part 1 flow works on the live URLs, on a real phone, with real photos, and survives bad input.

Step-by-step
1. Local run (laptop)

API: cd api && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env (fill keys) && uvicorn app.main:app --reload.
Web: cd web && npm install && cp .env.example .env.local && npm run dev.
Check http://localhost:8000/docs and http://localhost:3000.
2. Environment variables checklist (names only)

Render (API): SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, WEB_ORIGIN, DETECT_BACKEND=vlm, GEMINI_API_KEY, GEMINI_MODEL, CATALOG_PATH.
Vercel (web): NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL.
Catalog file: make sure data/catalog/appliance_catalog.csv is inside what Render deploys (if the Render root is api, copy the CSV into api/data/ or change the build to include it).
3. End-to-end checklist (do it on the live site, on a phone)

Sign up with a new email, create a home.
Upload 5 photos: AC outdoor unit with rating plate, AC indoor unit, ceiling fan, fridge, TV. Note which detections are wrong.
Review screen: correct one item, tick the rest, add them.
Add a missing item with catalog search; add 8 LED bulbs with the quick counter.
Report: calculate; compare the numbers by hand with a spreadsheet for 3 appliances (this is your sanity test).
Change sun hours to 6 and recalculate; confirm panel kW drops.
Log out, log in again: data is still there.
Second account: confirm it cannot see the first account's home.
Try bad input: 12 MB image, a PDF, a photo of a wall, airplane mode mid-upload, empty home report. Each must give a friendly message.
4. Fix order (priority)

Anything that loses or leaks data. 2. Anything that blocks the main flow. 3. Wrong numbers. 4. Confusing text. 5. Visual polish.
5. Performance and cold starts

Render free instances sleep; add a "Waking up the server (up to 1 minute)" message and a lightweight keep-alive: a free uptime monitor pinging /health every 10 minutes (use it only when demoing).
Detect call should finish within about 15 seconds; if not, check image resizing and the AI model name.
6. Demo data

Create a ready-made demo home "Demo House" with 10 realistic appliances so you can show the Report tab even if the AI service is unavailable.
Save 3 good demo photos and 3 tricky photos for the presentation.
7. Final deploy and repo hygiene

Merge to main, tag v0.1-part1. Confirm Vercel and Render redeploy.
README with: what the project is, architecture diagram (text is fine), how to run, environment variables (names), known limitations.
Update docs/HANDOFF.md with the live URLs and the list of known bugs.
Acceptance (Part 1 is "done" when all are true)
 The checklist in step 3 passes on a phone using the live URLs.
 A new person (a friend) can use it with no help in under 5 minutes.
 No secrets in the Git history; .env files ignored.
 The six bugs that remain are written down in HANDOFF.md.
Handoff
HANDOFF NOTE: final URLs, version tag, remaining known bugs sorted by severity.


