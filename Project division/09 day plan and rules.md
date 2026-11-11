Claude

















09 day plan and rules · MD
DAY PLAN, HANDOFF RULES AND PROMPT WRAPPER
(You keep this file; you do NOT paste it into the chunk chats.)

1. What is in the pack
File	Use
00_MASTER_BRIEF.md	Paste at the start of EVERY chat
schema.sql	Run once in Supabase SQL Editor (chunk 1, Part A)
01 setup/auth/deploy	Chunk 1
02 catalog	Chunks 2a, 2b, 2c (three chats, one section each)
03 sizing engine	Chunk 3
04 detect	Chunk 4
05 backend API	Chunk 5
06 frontend	Chunk 6
07 integration/deploy	Chunk 7
08 YOLO dataset/training	Chunk 8 (human photo work starts today)
2. Prompt wrapper (type this above the pasted brief and card in each new chat)
Role: you are the engineer for ONE chunk of my project. Below are (1) the MASTER BRIEF with contracts and (2) my TASK CARD.
Rules: follow the contracts exactly; do not ask questions unless blocked (state assumptions instead); give files one at a time with their exact path as heading; for fixes show only the changed part; end with the HANDOFF NOTE.
Start now with a plan of at most 6 bullets, then file 1.
If the chat stops because of the free-plan limit: open a new chat (any device), paste the wrapper, brief and card again, then paste the files already written and say "continue from file N".

3. Which chunk needs which files from other chunks
Chunk 1: nothing. Chunk 2a/2b/2c: nothing. Chunk 3: nothing. Chunk 4: nothing (fake catalog in tests).
Chunk 5: needs chunk 1 (auth.py, db.py, config.py, main.py), chunk 3 (function signatures), chunk 4 (detect.py, catalog.py, schemas.py).
Chunk 6: needs chunk 1 (web/, lib/api.ts) and chunk 5's HANDOFF NOTE (route examples).
Chunk 7: needs everything.
Chunk 8: nothing until it plugs into chunk 4's detect_yolo.py.
4. File ownership (avoids two chats editing the same file)
api/app/main.py: chunk 1 creates; chunk 5 edits to include routers.
api/app/schemas.py: chunk 4 creates (only DetectedItem); chunk 5 extends.
api/app/services/sizing.py, schedules.py: chunk 3 only.
api/app/services/catalog.py, detect*.py: chunk 4 only (chunk 8 edits detect_yolo.py later).
data/catalog/appliance_catalog.csv: you merge chunks 2a+2b+2c by hand.
web/: chunk 1 creates the shell; chunk 6 owns pages and components.
5. HANDOFF NOTE template (paste into docs/HANDOFF.md after every chunk)
## Chunk N — <name> — <date/time>
Files created: ...
Deviations from contracts: ...
Env vars added (names only): ...
How to test: ...
Open issues: ...
6. Today's schedule (Asia/Karachi). Adjust to your devices.
Time	Do
10:45–11:30	Human setup from chunk 1 Part A (GitHub, Supabase + schema.sql + bucket, Render, Vercel). Create a Gemini API key in Google AI Studio and check its free limits and current model names.
11:00 onward	Start in parallel on different devices: chunk 1, chunk 3, chunk 2a. Then 2b, 2c, chunk 4 as devices free up. Take 5–10 appliance photos during breaks (chunk 8).
13:30–15:00	Chunk 5 (after 1, 3, 4 are in the repo). Merge the three catalog CSVs into the repo.
15:00–17:30	Chunk 6 (frontend). Test on your phone as you go.
17:30–20:00	Chunk 7 (integration, bug fixing, deploy, demo data).
Evening	Chunk 8: photo collection and labeling test (20 photos).
7. If you fall behind, cut in this order (keep the core flow)
Print/PDF button, 2. Editable assumptions panel (keep a fixed default), 3. Quick counters, 4. Time-of-day editor (keep hours/day only), 5. Keep-alive and demo polish. NEVER cut: login, photo detect with review screen, editable list, sizing report, ownership checks.
8. Risks to check early today
Gemini free tier: limits, current model name, and its data-use terms (this affects the privacy text in the app).
Render free tier sleeps (30–60 s first request).
Catalog numbers are typical values, not verified. Show "typical value, please confirm" in the UI and verify the top rows against real nameplates this week.
Part 2 needs 7+ days of real check-ins: recruit 5–10 households by day 3 so data exists before your demo.
9. After today (preview, not for today)
Day 2: chunk 8 training + chunks 9 (bill OCR), 10 (weather/solar forecast). Day 3: chunk 11 (check-in + demand model), recruit users. Day 4: chunk 12 (recommendations), chunk 13 (what-if + PDF). Day 5+: evaluation, documents, demo; app (PWA install, Capacitor optional) next week; inverter simulator and error-code assistant last.


