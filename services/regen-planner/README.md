# DADI Regeneration Planner

A small module + CLI + optional FastAPI endpoints for planning deterministic regeneration when:

- prompt bundles change
- toolchain manifests change

It operates on the Postgres tables from the artifact store/orchestrator packs:
- `pipeline_runs`
- `stage_runs`
- `artifact_edges`
- `stage_cache`

## What it produces

A **regeneration plan** is a deterministic JSON document that answers:

- which pipeline runs are affected
- the earliest stage index to re-run per run
- the reason (prompt/toolchain change)
- what can be reused (stages before start index)
- which stages should be recomputed vs reused
- pointers to currently materialized stage outputs (by stage index)

This pack **does not** execute recomputation by default. Execution can remain manual, or you can wire `execute_plan()` to your orchestrator.

## Install

```bash
pip install -e .
```

## Database setup

Apply this extension:

```bash
psql "$DATABASE_URL" -f sql/regeneration_plans.sql
```

## CLI usage

Plan regeneration for prompt change:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/dadi"
python -m dadi_regen.cli plan \
  --old-prompt-sha <OLD_SHA> \
  --new-prompt-sha <NEW_SHA>
```

Plan regeneration for toolchain change:

```bash
python -m dadi_regen.cli plan \
  --old-toolchain-sha <OLD_SHA> \
  --new-toolchain-sha <NEW_SHA>
```

Fetch a plan:

```bash
python -m dadi_regen.cli get --plan-id <PLAN_ID>
```

## FastAPI (optional)

```bash
uvicorn dadi_regen.api:app --reload
```

Endpoints:
- `POST /plan/regenerate`
- `GET /plan/{plan_id}`
- `POST /execute/plan` (optional; default is no-op status update)
