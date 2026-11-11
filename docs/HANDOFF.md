# Project handoff

## Implemented

- FastAPI foundation, Supabase bearer-token validation, service-role database
  access, CORS, health endpoint, request IDs, and sanitized API errors.
- Home and appliance CRUD with ownership checks, 24-hour schedules, catalog
  search, sizing reports, and account-scoped data access.
- Deterministic sizing engine, default schedules, initial 44-row catalog,
  worked-example tests, and sizing notes.
- Gemini photo-detection adapter, normalized/catalog-tagged results, private
  upload support, opt-in image retention, and YOLO integration stub.
- Next.js landing page, Supabase sign-up/sign-in, protected dashboard, home and
  appliance workflow, photo review, manual entry, and sizing report charts.

## Human setup still required

- Create Supabase, Render, Vercel, and Gemini accounts; provide the API keys in
  local/deployment environment settings (never in source files).
- Run `sql/schema.sql`, create the private `appliance-images` bucket, and
  configure Supabase email-confirmation and redirect URLs.
- Choose a current Gemini model available to the account and set `GEMINI_MODEL`.
- Collect and label permitted appliance photos before training or enabling YOLO.
- Deploy services and verify the full two-account ownership flow using real
  Supabase users.

## Known gaps

- No live Supabase project or deployment URLs are available in this workspace.
- The YOLO backend is intentionally not implemented until a labeled dataset
  and trained weights exist.
- Future product phases (weather/consumption forecasts and inverter
  simulator/error-code assistant) remain out of Part 1 scope.

## Local verification

- `api`: 22 pytest tests pass; application and scripts compile.
- `web`: ESLint, TypeScript, and production build pass.
- Landing page responds locally and has no horizontal overflow at a 360 px
  viewport.
- Live sign-up, database, storage, and deployment checks remain blocked on
  user-owned service accounts and credentials.
- A disposable Supabase user was created and deleted for live API verification.
  Home creation, 10-appliance bulk insertion, 24-hour schedule generation,
  sizing, report retrieval, and cleanup all passed. No test data was left behind.
- The signed-in dashboard now offers an explicit "Add sample home" action so
  the owner can load a 10-appliance sample and sizing report into their account.
