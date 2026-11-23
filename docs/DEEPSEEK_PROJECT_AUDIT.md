# Solar Care AI — Project Audit and DeepSeek Context

**Audit snapshot:** repository commit `f6f5648` (`update code`), 2026-11-23  
**Purpose:** Give a coding assistant enough grounded context to understand what this repository builds, how it works, and what is not yet implemented. This is a codebase orientation, not a claim of independent field validation.

## 1. Product summary

Solar Care AI is a mobile-first web application for households in Pakistan to explore solar-system options using their home and appliance information. A user can create a home, add and edit appliances and their daily schedules, estimate household energy use, and compare on-grid, hybrid, and off-grid planning sizes.

The application also includes bill entry and calibration, weather-aware forecasts, daily usage check-ins, demand estimates, recommendations for shifting flexible loads, and a what-if solar-system comparison. Photo detection helps start an appliance inventory, but the result is explicitly intended for user review. The system sizing engine is deterministic; it is not an ML sizing model.

All sizing, generation, demand, tariff, and savings numbers are planning estimates. They are not an installation design, an installer quotation, guaranteed savings, or a substitute for checking appliance labels and site conditions with a qualified solar installer.

## 2. Main user journey

1. A user signs up or signs in with Supabase Auth.
2. They create a home and can provide location and household details.
3. They add appliances manually or start from an appliance photo. Detected items are reviewed and editable before becoming the home inventory.
4. The user can set appliance quantities, power values, essential-load status, and a 24-hour use schedule.
5. The API estimates daily energy and produces on-grid, hybrid, and off-grid system options, with assumptions, load profiles, breakdowns, and warnings.
6. Additional screens let the user record electricity bills and daily check-ins, inspect forecasts and demand estimates, explore recommendations, and compare system scenarios.
7. The model-transparency page reports available local metadata and whether optional artifacts are present; it does not itself evaluate model accuracy.

## 3. Architecture and responsibilities

| Area | Technology | Responsibility |
|---|---|---|
| `web/` | Next.js App Router, React, TypeScript, Supabase client, Recharts | Landing/auth screens, protected home workflows, forms, charts, model-transparency UI |
| `api/` | FastAPI, Pydantic, Supabase Python client | Authenticated API, ownership checks, business logic, catalog/bill/photo/weather operations |
| `sql/` | PostgreSQL/Supabase SQL | Homes, appliance catalog, home appliances, detections, bills, daily logs, sizing reports, access policies, and Part 2 tables |
| `data/catalog/` | CSV | Source data used to seed the shared appliance catalog |
| `ml/` | Python scripts | Dataset/training entry points; current training scripts are placeholders, not a completed training pipeline |
| `docs/` | Markdown and generated SVGs | Sizing explanation, evaluation protocol/results, project handoff |

The website calls the API through `web/src/lib/api.ts`. Requests include the signed-in Supabase access token. The API validates the token and uses its Supabase service-role client for database operations, so home-scoped routes must enforce explicit ownership checks. Never expose the service-role key to the browser or commit environment files.

The main API modules are registered in `api/app/main.py`. Broadly, routers cover homes, appliances, catalog, detections, sizing, bills, forecasts, check-ins/demand, recommendations, what-if comparisons, and model metadata. `/health` is the unauthenticated health check; `/me` is an authenticated identity check.

## 4. Implemented product areas

### Home and appliance inventory

- Users can create, view, update, and delete their homes.
- Home appliances support editable type, brand/model, watts, quantity, duty/surge factors, schedule, and essential-load flag.
- The shared catalog supports appliance search and defaults. Catalog values are estimates; the repository describes the initial catalog as 44 rows, and its values are not all independently verified.
- `source_tag` distinguishes `label`, `catalog`, `guess`, and `user` values, with confidence and verification fields to retain provenance.

### Photo-based appliance detection

- The detect endpoint accepts an appliance photo, applies image handling/rate limiting, and returns a reviewable inventory suggestion.
- The VLM adapter uses Gemini when configured. Post-processing normalizes appliance types, extracts visible capacity/power text where possible, matches catalog entries, supplies typical fallbacks, and marks the value source/confidence.
- Users can edit the proposal and finalize the detection into home appliances.
- The backend now recognizes `vlm`, `yolo`, and `hybrid` settings. `hybrid` tries YOLO and falls back to VLM on a `DetectionError`.
- Detection image retention is opt-in. The bill-photo flow asks for explicit consent before sending a selected image to Gemini; see the bill router/service for exact flow.

**Readiness:** Gemini detection depends on user-provided API configuration and upstream availability. A YOLO inference path exists in `api/app/services/detect_yolo.py`, but this checkout does not contain trained `api/models/best.pt` weights, a dataset, or a completed training workflow. The inference runtime is imported optionally and is not listed in `api/requirements.txt`. Do not describe YOLO as a trained or validated production model.

### Deterministic system sizing

`api/app/services/sizing.py` estimates:

- Daily, day-time, and night-time energy from watts, quantity, duty factor, and hourly schedule.
- Connected and peak loads, including a startup-surge allowance.
- Standard inverter sizing with configurable margin and warnings for unusual loads.
- On-grid, hybrid, and off-grid panel/inverter/battery options.

The engine has explicit assumptions (for example peak sun hours, system efficiency, battery depth of discharge/efficiency, autonomy, and outage duration). These are configurable calculation inputs, not learned parameters. See `docs/sizing.md`.

### Bills, calibration, weather, and demand

- Bills can be recorded and listed per home; bill-photo OCR/parsing is implemented as an optional assisted flow.
- Bill history can calibrate the appliance-based monthly estimate with a bounded overall scale.
- Forecast and daily demand services use Open-Meteo data with cache/fallback behavior. Where location/weather is missing, the app may use neutral weather or approximate climate normals; these are not site-grade measurements.
- Demand estimation in `api/app/services/demand.py` uses appliance schedules, temperature/degree-hours, optional check-in context, and per-home scaling parameters/residuals where enough history exists. Confidence labels are based on available history and residual evidence.
- The check-in feature records daily usage/context; demand and verdict endpoints expose the resulting estimate/interpretation.

**ML distinction:** There is no functioning global demand-model training-and-inference pipeline in this snapshot. `ml/demand/train_demand.py` exits with an intentional placeholder message. `demand_features.py` computes candidate features, while `demand_ml.py` does not load or apply a trained prediction artifact; both artifact-present and artifact-absent branches currently return the same physics prediction with a label. The separate per-home scale fit is not the same thing as a trained global model. Treat ML labels and metadata as transparency/UI scaffolding unless a real artifact, verified inference path, and evaluation are added.

### Forecast, recommendations, and what-if

- Forecast routes provide weather/solar-related information for the home.
- The recommendation optimizer ranks flexible-appliance schedule shifts against solar/load profiles and reports estimated grid-import changes. Recommendations and feedback are not evidence of actual savings unless measured and evaluated with real data.
- The what-if service compares grid-tied, hybrid, and expanded system scenarios using modeled daily profiles across representative monthly weather. It provides sensitivity variants, not a year of measured operation.
- Tariff-cost outputs remain unavailable or limited when the tariff input is a placeholder. Do not infer current Pakistani tariff rates from the code.

### Model transparency

`GET /models/info` and the `/about-models` screen report local artifact/metadata presence, detector classes/backend setting, demand metadata, and evaluation-document presence. Presence checks do not prove an artifact is valid, used, accurate, or production-ready.

## 5. Data and security model

The SQL schema includes:

- `homes`, owned by Supabase Auth users.
- `home_appliances`, `detections`, `bills`, `daily_logs`, and `sizing_reports`, associated with a home.
- `appliance_catalog`, readable by authenticated users.
- Part 2 migration tables including `weather_cache`, `demand_models`, and `recommendation_feedback`.

Row-level security policies are defined in the schema/migration. The API also uses explicit ownership dependencies because it uses the service-role key, which bypasses normal end-user RLS behavior. Changes to a home-scoped route must preserve both authorization and ownership checks. Private image storage must stay private.

Required service credentials are configured through local/deployment environment variables (see `api/.env.example` and `web/.env.example`). Actual `.env` files are ignored and must not be read into this document, pasted into prompts, or committed.

## 6. Current maturity and known limitations

Treat these as the important state-of-project facts:

1. **The core value is a planning workflow, not a certified engineering design.** Schedules, wattages, duty factors, local weather, equipment assumptions, and site details can be wrong or incomplete.
2. **Real-world evaluation data is not bundled.** The evaluation documentation explicitly separates synthetic test/evaluation results from real household, bill, detection, feedback, and user-study evidence. Synthetic scores must never be presented as real-world accuracy.
3. **The appliance catalog contains estimates.** Users should verify the actual appliance label and operating conditions.
4. **YOLO is not trained/ready in this checkout.** The inference entry point exists, but model weights and a labeled dataset are absent; training scripts do not train a model yet.
5. **Global demand ML is not implemented end-to-end.** Current demand estimates are primarily physics/rule-based with per-home fitting/calibration, not global model inference.
6. **Tariff and payback claims require current inputs.** Do not invent rates, prices, or savings to fill missing data.
7. **Weather fallback is approximate.** Weather can be stale, cached, neutral, or based on climate normals; the UI/API should retain that distinction.
8. **Operational scale is limited.** Image rate limiting is in-memory per API process; horizontal scaling requires a shared limiter. External services and credentials (Supabase, Gemini, weather, deployment) are user-owned setup.
9. **Some older project prose is stale.** `README.md` and `docs/HANDOFF.md` still describe YOLO as an integration stub/not implemented. The current source has a conditional inference path; neither statement should be read as proof of a trained or deployable detector.

Before making a claim about a feature, check its route/service and tests, not only an older handoff or a model-info badge.

## 7. Local development and verification

Use the repository README for the full Windows setup. At a high level:

1. Create/configure Supabase; apply `sql/schema.sql` and `sql/migrations/002_part2.sql`; create the private `appliance-images` bucket if using image features.
2. Copy the example environment files to local `.env` files and provide credentials privately. Keep the Supabase service-role key API-only.
3. Install API dependencies from `api/requirements.txt`, run the API from `api/` with `uvicorn app.main:app --reload`.
4. Install web dependencies from `web/`, then run `npm run dev`.

Useful checks:

```powershell
# From api/
python -m pytest -q

# From web/
npm run lint
npx tsc --noEmit
npm run build
```

The repository includes API test modules for sizing, demand, detection, bills, forecasts, recommendations, weather, and what-if behavior. A passing local unit suite does not verify live Supabase/Gemini integrations or real-world model quality. Live checks require user-owned services and valid credentials.

## 8. Guidance for a coding assistant

- Start by reading this document and `README.md`; then inspect the specific route, service, schema, and tests before changing behavior.
- Preserve the separation between deterministic sizing and optional prediction/vision components.
- Preserve ownership checks, server-only secrets, opt-in image retention, and user review of detected values.
- Do not claim training, accuracy, tariff correctness, savings, or real-world validation without artifacts and reproducible evidence.
- If adding an ML model, specify and implement the full path: permissioned data, reproducible preprocessing/training, artifact format/location, dependency/runtime, inference integration, version/metadata, fallback behavior, and time-appropriate evaluation against baselines.
- Keep synthetic evidence visibly labeled and separate from real observations.
- Update stale README/handoff statements when the corresponding code state changes.
