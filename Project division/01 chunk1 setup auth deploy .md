
01 chunk1 setup auth deploy · MD
# CHUNK 1 — Foundation: repo, auth, database, deploy skeleton
(Paste MASTER BRIEF first, then this card. Do this chat FIRST. Other chats can start in parallel because they only need the brief.)
 
## Goal
A live website where a user can sign up, log in, and see a protected dashboard, plus a live API with /health and /me. Database tables exist with security rules. Nothing else.
 
## Part A — what YOU (the human) do by hand (Claude cannot do these for you)
1. Create a GitHub repo `solar-care-ai` (private). Clone it on your laptop.
2. Create a Supabase project (free). Copy: Project URL, anon/publishable key, service-role key (secret).
3. In Supabase SQL Editor run `schema.sql` (the file in this pack). Check that 7 tables appear.
4. Storage -> New bucket `appliance-images`, public OFF.
5. Auth -> Providers -> Email: for testing today, turn OFF "confirm email" so signup works instantly. Turn it back ON before real users.
6. Create a free Render account and a free Vercel account (sign in with GitHub).
## Part B — ask Claude to write (one file at a time)
### B1. Web app (folder `web/`)
- Next.js (App Router, TypeScript, Tailwind). Packages: `@supabase/supabase-js`, `@supabase/ssr`, `recharts`.
- `src/lib/supabase/client.ts`, `server.ts`, and `middleware.ts` that redirects logged-out users from `/dashboard` and `/homes/*` to `/login`.
- Pages: `/` (landing: one sentence of what the app does + Login/Sign up buttons), `/login`, `/signup`, `/dashboard` (shows user email, logout button, empty "Your homes" list placeholder).
- `src/lib/api.ts`: `apiFetch(path, options)` that reads the Supabase session, adds `Authorization: Bearer <access_token>`, calls `NEXT_PUBLIC_API_URL`, throws readable errors.
- PWA basics: `public/manifest.webmanifest` (name "Solar Care AI", short_name "SolarCare", display standalone, theme color, 192/512 icons placeholders), manifest link and viewport meta in the layout. No service worker today.
- `.env.example` with `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`.
- Mobile-first layout: max width container, bottom spacing, large tap targets.
### B2. API (folder `api/`)
- `requirements.txt`: fastapi, uvicorn[standard], pydantic-settings, httpx, supabase, python-multipart, pillow, rapidfuzz, pytest.
- `app/config.py` (pydantic-settings: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, WEB_ORIGIN, DETECT_BACKEND, GEMINI_API_KEY, GEMINI_MODEL).
- `app/db.py`: one supabase client created with the service-role key.
- `app/auth.py`: `get_current_user` dependency. It reads the bearer token and calls `GET {SUPABASE_URL}/auth/v1/user` with headers `Authorization: Bearer <token>` and `apikey: <anon key>`. 401 if invalid. Cache a valid token for 60 seconds in memory. Return `{id, email}`.
- `app/main.py`: FastAPI app, CORS allowing `WEB_ORIGIN` and `http://localhost:3000`, `GET /health` -> `{"ok": true}`, `GET /me` (auth required) -> user id and email. Include empty routers for later chunks.
- `.env.example`, `README` with run commands (`uvicorn app.main:app --reload`).
### B3. Deploy files
- `api/render.yaml` or clear Render dashboard instructions: root dir `api`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check path `/health`, Python 3.11.
- Vercel instructions: import repo, root directory `web`, the three env vars.
- Supabase Auth URL settings: Site URL = Vercel URL, add `http://localhost:3000` to redirect URLs.
## Acceptance checks (all must pass)
- [ ] Sign up with a new email, log in, see `/dashboard`; logging out and opening `/dashboard` redirects to `/login`.
- [ ] `https://<render-url>/health` returns ok.
- [ ] Calling `/me` from the web app (add a temporary button) returns your user id; without a token returns 401.
- [ ] Two accounts: create a row in `homes` for account A via the SQL editor; confirm account B cannot read it (RLS works) when querying from the web client.
- [ ] The service-role key appears ONLY in Render env vars and your local `api/.env`, never in `web/`.
## Known traps (tell Claude about them)
- Render free instances sleep; the first request can take 30-60 seconds. Add a friendly "waking server..." message on the web side later.
- Keep `.env` files out of Git (`.gitignore`).
- New Supabase projects may call the anon key "publishable key"; either works as `apikey`.
## Handoff
End with a HANDOFF NOTE and add it to `docs/HANDOFF.md`. Also write the live URLs and which env vars are set (names only, never values).
 
