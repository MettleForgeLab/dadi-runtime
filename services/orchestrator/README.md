# DADI Orchestrator (Execution Discipline)

This package provides a deterministic orchestrator that enforces:

- Stage boundaries via `stage_input-v1` artifacts
- Fail-closed validation for stage inputs and outputs (Draft 2020-12 JSON Schema)
- Content-addressed artifacts (SHA256)
- Lineage edges (`artifact_edges`)
- Memoization (`stage_cache`) keyed by deterministic stage inputs

## Setup

Apply the storage schema and orchestrator extensions:

```bash
psql "$DATABASE_URL" -f sql/schema.sql
psql "$DATABASE_URL" -f sql/orchestrator_extensions.sql
```

Install:

```bash
pip install -e .
```

## Run the example

Set required environment variables:

- `DATABASE_URL`
- `PIPELINE_RUN_ID`
- `DOCPACK_SHA256`
- `TOOLCHAIN_SHA256`
- `PROMPT_SHA256`

Then:

```bash
python -m examples.run_pipeline
```

## Execution discipline

For each stage, the orchestrator:

1. Builds canonical `stage_input-v1` JSON.
2. Validates stage input schema (fail-closed).
3. Stores stage input artifact.
4. Performs memoization lookup keyed by stage input hash.
5. On cache miss, executes the stage handler.
6. Validates stage output schema (fail-closed).
7. Stores stage output artifact.
8. Records lineage edges and stage cache mapping.
9. Marks stage_run success/fail_closed in the database.

This gives replayability and debugging without relying on LLM determinism.
