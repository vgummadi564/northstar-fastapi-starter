# Northstar — FastAPI starter

Backend starter for **From Context to Confidence**, designed for the accompanying Northstar synthetic Supabase PostgreSQL dataset. It supports **live OpenAI-generated SQL** and **explicitly labeled replay queries**, both executed against the actual database. It does not hardcode the financial result.

## What it includes

- `GET /api/health`, `/api/scenarios`, `/api/tables`, `/api/tables/{table_name}`
- `GET /api/context/{scenario}` (approved policy evidence)
- `POST /api/ask` (`without_context` or `with_context`)
- `POST /api/recalculate` (always `with_context`)
- `GET /api/audit/{run_id}`
- `/docs` Swagger API explorer
- PostgreSQL connection via psycopg, OpenAI chat completions, conservative SQL AST validation, per-query read-only transactions and timeouts

## Prerequisites

1. Load the **Northstar dataset** using its `01_schema.sql` and CSV files, then run `02_validate.sql`. Do not execute that schema against important data; it drops ten named tables.
2. Python 3.11+ and a Supabase PostgreSQL connection string from **Supabase Dashboard → Connect**. Use the session pooler if your hosting environment cannot use direct IPv6 connections.
3. An OpenAI API key (billing may apply).
4. Two PostgreSQL roles with separate credentials. Never use the Supabase `service_role` browser key as a PostgreSQL connection string.

## Role setup

Review `sql/roles_example.sql` in Supabase SQL Editor. It contains sample role creation and grants; replace example passwords before execution. **Do not commit passwords or execute blindly.** The readonly role sees only the six financial tables. The backend role sees only approved context tables and can write/read audit records. The schema's public tables may also have grants to `anon`/`authenticated`; review Supabase API exposure/RLS before making the demo public. For production, put sensitive tables in a non-exposed schema, enable appropriate RLS and use a private API with authentication and rate limits.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
# Edit .env with two PostgreSQL URLs and an OpenAI API key
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000/docs. `.env` is excluded by `.gitignore`.

## Example calls

```bash
curl http://127.0.0.1:8000/api/scenarios
curl -X POST http://127.0.0.1:8000/api/ask -H 'Content-Type: application/json' -d '{"scenario":"bookings_vs_revenue","question":"What was our recognized subscription revenue in 2025?","mode":"without_context","execution":"live"}'
curl -X POST http://127.0.0.1:8000/api/recalculate -H 'Content-Type: application/json' -d '{"scenario":"bookings_vs_revenue","question":"What was our recognized subscription revenue in 2025?","execution":"live"}'
```

For a repeatable, **clearly labeled replay**, change `execution` to `replay`. The SQL is curated, but **the numerical result is still queried from Supabase**. In `live` mode, the LLM may select the correct table without policies; that is a valid observation, not a failure of the demo.

Other scenario: `gross_vs_net`, question `What were our net sales in 2025 after refunds and credits?`

## Example React integration

```js
const response = await fetch(`${import.meta.env.VITE_API_URL}/api/ask`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    scenario: 'bookings_vs_revenue',
    question: 'What was our recognized subscription revenue in 2025?',
    mode: 'without_context',
    execution: 'live'
  })
});
if (!response.ok) throw new Error('Request failed');
const run = await response.json();
console.log(run.sql, run.result.answer, run.validation, run.run_id);
```

## Limitations and hardening before public deployment

- **Prototype, not a hardened public service.** There is no authentication, rate limiting, budget enforcement, or concurrency control. Add these before publishing; especially protect `/api/context`, `/api/audit` and table previews.
- SQL guard permits **one simple aggregate SELECT from one allowlisted financial table**. This is deliberate. It rejects joins needed for some advanced analysis, such as prior-year recognition split. Add vetted query templates or a separately reviewed AST policy for joins.
- The database role, not SQL parsing, is the final security boundary. Enforce SELECT-only grants, RLS where applicable, query timeouts, network controls and resource budgets.
- In `without_context` the prompt has table/column names and data types but **no approved policies or metric definitions**. Column names still provide semantic clues; the model may get the right answer. In `with_context`, approved policies and definitions are retrieved by backend.
- The financial validation is a **demo-target check**, not an independent general accounting validator. Compare to the dataset's `02_validate.sql` and build stronger domain-specific tests for production.
- The starter uses the supplied Northstar dataset's table and column names. It has not been connected to your Supabase instance or OpenAI account in this environment.
- Data access is synchronous and opens a DB connection per request, suitable for a small demo. For scale, use a pool, async I/O and observability.
- `OPENAI_MODEL` must support `response_format={"type":"json_object"}`. Set a compatible model available to your API account.

## Deployment

Deploy FastAPI on Render or a similar Python host. Build: `pip install -r requirements.txt`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Configure secrets in host environment; set `CORS_ORIGINS` to the exact deployed React origin. Keep database connection strings and OpenAI key server-side. Do not commit `.env`.

## Tests

```bash
pytest -q
```
