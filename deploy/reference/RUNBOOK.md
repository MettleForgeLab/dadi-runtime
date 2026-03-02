# Reference Deployment Pack (Happy Path)

This pack stands up:
- Postgres
- DADI Gateway (unified API)
- Artifact Browser UI

It also includes a seed script that creates a minimal end-to-end demo state:
- Stores a `docpack-v1` artifact
- Stores placeholder `toolchain_manifest-v1` and `prompt_bundle-v1`
- Creates a pipeline and pipeline_run
- Stores Stage 02 input/output artifacts
- Records lineage edges and memoization cache
- Inserts a stage_run row (for planning)
- Creates a regeneration plan and verifies `/explain`

## Quickstart

1) Start services:

```bash
docker compose up --build
```

2) Seed demo state (from your host shell):

```bash
pip install psycopg[binary] requests
export API_BASE="http://localhost:8000"
export DATABASE_URL="postgresql://dadi:dadi@localhost:5432/dadi"
python scripts/seed_demo.py
```

3) Open UI:

- http://localhost:3000

## What to try in the UI

### Artifact
Paste the printed `docpack_sha256` or `stage02_output_sha256` into the Artifact tab.

You should see:
- artifact metadata
- JSON content preview
- upstream/downstream edges

### Plan
Paste the printed `plan_id` into the Plan tab.

You should see:
- plan items with reuse/recompute stages
- explain payload showing which stage_run matched the old prompt hash

### Diff
Use the Diff tab to compare:
- stage input vs stage output (both JSON)
- or compare two different JSON artifacts

## Notes

- This is a minimal happy path. It does not run the orchestrator or call an LLM.
- The purpose is to prove: storage + lineage + cache + planning + UI interlock cleanly.


## JWT dev tokens

Generate a token for a tenant:

```bash
python scripts/jwtgen.py --tenant tenant_a --scope artifact:read_bytes
```

Set UI token:

```bash
export NEXT_PUBLIC_AUTH_TOKEN=<token>
```
