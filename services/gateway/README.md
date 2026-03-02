# DADI Gateway (Thin Unified API)

This is a thin FastAPI gateway that mounts a unified API surface over a shared Postgres database.

It provides:

- Artifacts:
  - `POST /artifacts`
  - `GET /artifacts/{sha256}`
  - `GET /artifacts/{sha256}/content`
- Lineage:
  - `POST /edges`
  - `GET /lineage/{sha256}/upstream`
  - `GET /lineage/{sha256}/downstream`
- Cache:
  - `GET /cache/lookup`
  - `POST /cache/record`
- Regeneration plans:
  - `POST /plan/regenerate`
  - `GET /plan/{plan_id}`
  - `GET /plan/{plan_id}/explain`
  - `POST /execute/plan` (status update only; execution remains manual by default)
- Health:
  - `GET /health`

This gateway assumes the database schema from the artifact store/orchestrator packs plus regeneration planner extensions:
- `sql/schema.sql` (artifact store/orchestrator)
- `sql/regeneration_plans.sql` (planner)

## Setup

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/dadi"
psql "$DATABASE_URL" -f sql/schema.sql
psql "$DATABASE_URL" -f sql/regeneration_plans.sql
```

Run:

```bash
uvicorn dadi_gateway.app:app --reload --port 8000
```

Point the UI to:

```bash
export NEXT_PUBLIC_API_BASE="http://localhost:8000"
```

## Notes

- Auth is not implemented in this pack. Add auth at the gateway boundary.
- This gateway is intentionally thin: it performs no orchestration and no LLM calls.
