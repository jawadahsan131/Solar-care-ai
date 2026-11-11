# PREFLIGHT — verify Copilot's Part 1 before building Part 2
(Do this FIRST. About 30-45 minutes. Copilot's summary says what files exist; it does not prove they work. Part 2 stands on Part 1, so a hidden bug here costs you days later.)

## A. Human checks (you, on your Windows machine)
1. **Secrets safe?** In PowerShell from repo root: `git check-ignore -v api/.env web/.env.local` must print a rule for both. Then `git log --all -p -S"service_role" -- .` must show no real key (only variable names).
2. **Supabase setup done?** (project, `sql/schema.sql` run, private bucket `appliance-images`, Auth redirect URLs, `api/.env` and `web/.env.local` filled). If not, finish it first: tell me which step you are on.
3. **Run it locally**
   - API: `cd api; python -m venv .venv; .venv\Scripts\activate; pip install -r requirements.txt; pytest` then `uvicorn app.main:app --reload` and open `http://localhost:8000/docs`.
   - Web: `cd web; npm install; npm run dev`, open `http://localhost:3000`.
4. Do the 9-step end-to-end test from `07_CHUNK7_integration_deploy.md` step 3 on your laptop. Write every failure in a list.

## B. Copilot audit prompt (paste into Copilot Chat with the repo open)
```
Audit this repo against docs/pack/00_MASTER_BRIEF.md. Do NOT add features. Report only, as a table: item | status (OK / BROKEN / MISSING) | evidence (file + line) | fix.
Check:
1. Every home-scoped route verifies the home belongs to the logged-in user (list each route and how). Same for /appliances/{id} and /detections/{id}/finalize.
2. SUPABASE_SERVICE_ROLE_KEY is never referenced in web/ and never printed in logs.
3. Appliance create/bulk stores hourly_use with exactly 24 numbers in 0..1; PATCH sets user_verified=true and source_tag="user".
4. sizing.py reproduces this example: AC 1200W duty .6 surge 2 on hours 13-20; 3 fans 75W on hours 10-21 (essential); fridge 150W duty .4 surge 3 all day (essential); 8 LED 12W hours 18-23 (essential). Expected daily 10.476 kWh, night 4.416, peak 2.871, inverter 3.6, on-grid panel 2.79, off-grid panel 3.21 + battery 6.13 kWh, hybrid panel 3.07 + battery 2.62 kWh. Run the test and show the output.
5. data/catalog/appliance_catalog.csv exists, has the 13 columns in the brief's order, every type is an allowed slug, duty 0..1, surge >=1, and row count. Say how many rows are type-level vs brand rows.
6. Detection: image size/type limits, friendly error on provider failure, no image bytes in logs, rate limit exists.
7. Run pytest and paste the full result. List tests that are skipped or mocked.
8. Any hard-coded secrets, TODOs, or fake/stub implementations pretending to work.
```
Bring the table back to Claude only for rows that are BROKEN or MISSING.

## C. Gate (all must be true to start Part 2)
- [ ] Local end-to-end test passes (login, home, photo or manual add, edit, report).
- [ ] pytest passes and the sizing example matches.
- [ ] Two-account ownership test passes.
- [ ] Catalog CSV has at least 60 rows.
- [ ] Nothing secret in Git.
If a row fails, fix it first with one short chat per bug. Deployment (Render + Vercel) can run in parallel with the first Part 2 chunks, because chunks 9 and 10 do not need the live site, but real users need it by day 3.
