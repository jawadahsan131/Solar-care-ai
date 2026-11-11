# Solar Care AI API

FastAPI backend for Solar Care AI.

## Local development

From the `api` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Set Supabase values in `.env` before using authenticated endpoints. The service-role
key belongs only in this API environment; never put it in the web app.

- Health: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>
