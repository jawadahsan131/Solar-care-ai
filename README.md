# Solar Care AI

A mobile-first solar-planning app for households in Pakistan. Users create a
home, build an editable appliance list manually or from a photo, and compare
deterministic on-grid, hybrid, and off-grid system estimates.

Automatic detection is a starting point, not an authority: users can correct
the appliance type, label values, watts, quantity, and schedule. The sizing
engine is deterministic Python; Gemini is used only for image detection and
visible label text.

## Architecture

- `web/`: Next.js App Router, TypeScript, Tailwind CSS, Supabase Auth, Recharts.
- `api/`: FastAPI, Pydantic, Supabase service-role access, Pillow, Gemini SDK.
- `data/catalog/appliance_catalog.csv`: source data for the Supabase appliance catalog seed.
- `sql/schema.sql`: Supabase tables and row-level security policies.
- `sql/migrations/002_part2.sql`: bill, weather-cache, and later Part 2 data.
- `docs/sizing.md`: sizing formulas in plain language.
- `docs/evaluation.md`: evaluation protocol, generated results, and known gaps.
- `data/tariff.json`: editable tariff input; cost estimates stay disabled while it is a placeholder.

The API uses the Supabase service-role key and therefore performs explicit
ownership checks for every home-scoped request. The key must never be exposed
to the browser. Catalog search and appliance defaults are read from
`public.appliance_catalog`; the CSV is only the seed source.

## Run locally on Windows

1. Create a Supabase project. Run `sql/schema.sql` and then
   `sql/migrations/002_part2.sql` in its SQL Editor. Create a **private** Storage
   bucket named `appliance-images`.
2. Copy `api/.env.example` to `api/.env`, and `web/.env.example` to
   `web/.env.local`. Set the Supabase URL and public anon key in both. Set the
   service-role key only in `api/.env`. Photo detection also needs a Gemini API
   key and model name.
3. Seed the shared catalog once, from PowerShell:

   ```powershell
   cd api
   python ..\scripts\seed_catalog.py
   ```

   This uses the service-role key from `api/.env` and upserts the CSV rows
   without deleting existing catalog records. `public.appliance_catalog` must
   exist first; `sql_002_part2.sql` does not create or seed it.
4. In PowerShell, start the API:

   ```powershell
   cd api
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

5. In another PowerShell window, start the website:

   ```powershell
   cd web
   npm install
   npm run dev
   ```

Open <http://localhost:3000>. API docs are at <http://localhost:8000/docs>.
The website can be built without credentials; authentication and data actions
require valid Supabase configuration.

## Tests and checks

From `api/`:

```powershell
python -m pytest -q
$env:SOLAR_ACCESS_TOKEN = "<your Supabase access token>"
.\scripts\smoke_test.ps1
```

From `web/`:

```powershell
npm run lint
npx tsc --noEmit
npm run build
```

## Environment variable names

API: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
`WEB_ORIGIN`, `DETECT_BACKEND`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and
`CATALOG_PATH` (the CSV path used only by the seed script).

Web: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
`NEXT_PUBLIC_API_URL`.

Never commit `.env` or `.env.local` files or put the service-role key in the
web environment.

## Deployment

Deploy `web/` as a Vercel project and `api/` as a Render web service. Configure
the variables listed above in the corresponding service environments and set
`WEB_ORIGIN` to the deployed website origin. The Render blueprint is
`render.yaml`. Run the catalog seed command once after creating the Supabase
schema; keep `data/catalog/` in the deployment repository for future catalog
updates.

## Part 2 features

The home app includes bills and calibration, weather and solar forecasts,
check-ins and demand estimates, recommendations, a daily dashboard, and a
what-if system comparison. The report can be printed or saved to PDF from the
browser. Run `python scripts/evaluate.py` to refresh the synthetic and optional
CSV-based evaluation tables and charts.

## Current limitations

- Catalog rows are typical estimates, all unverified; check actual appliance
  labels before installation.
- Gemini photo detection requires a user-provided API key/model and may be
  unavailable at free-tier limits. Bill-photo reading also sends the selected
  image to Gemini only after the user gives explicit consent; images are not
  stored by the app.
- Weather forecasts use Open-Meteo. If the service is unavailable, the API uses
  cached weather or clearly labelled approximate climate normals; the normals
  should be replaced with archive-derived averages before relying on them.
- YOLO is an explicit not-yet-trained backend stub. Private, permissioned image
  collection and labeling are human tasks.
- What-if results use approximate monthly climate normals and modeled appliance
  schedules; they are planning estimates, not an installer quotation.
- Tariff cost estimates remain unavailable until official current slab rates
  and charges are entered in `data/tariff.json`.
- No real labelled-photo, household-meter, or user-study evaluation sample is
  bundled. Synthetic evaluation results are not real-world accuracy claims.
- In-memory photo rate limits are shared between detection and bill-photo
  reading within one API process; use a distributed limiter before scaling out.
- Estimates are not an installation design; use a qualified solar installer.
