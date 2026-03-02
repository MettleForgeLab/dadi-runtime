# DADI Artifact Store + Lineage Graph + Memoization Layer

This pack provides a minimal, enforceable storage layer for deterministic, multi-stage pipelines:

- **Artifact store** (immutable, SHA256-addressed)
- **Lineage graph** (artifact-to-artifact edges)
- **Memoization layer** (stage input → stage output cache)
- **FastAPI service** exposing core operations

## Key guarantees (structural)

- Artifacts are **content-addressed**: `sha256` is the primary key.
- Artifact writes are **idempotent**: re-putting the same bytes is a no-op.
- Artifacts are **immutable**: no overwrites; different bytes → different SHA256.
- Lineage edges are **append-only**.
- Memoization is keyed by **stage_name + stage_schema_version + input_artifact_sha256**.

## Install

```bash
pip install -e .
```

## Setup database

Apply schema:

```bash
psql "$DATABASE_URL" -f sql/schema.sql
```

## Run API

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/dadi"
uvicorn dadi_store.app:app --reload
```

## API endpoints (minimal)

- `POST /artifacts` — store artifact bytes + metadata (idempotent)
- `GET /artifacts/{sha256}` — metadata
- `GET /artifacts/{sha256}/content` — bytes
- `POST /edges` — record lineage edge
- `GET /lineage/{sha256}/upstream` — edges into artifact
- `GET /lineage/{sha256}/downstream` — edges out of artifact
- `GET /cache/lookup` — memoization lookup for a stage input
- `POST /cache/record` — record memoization mapping

## Intended integration

In a 6-stage pipeline, for each stage:

1) validate + canonicalize input JSON → compute input SHA256  
2) `GET /cache/lookup?stage_name=...&stage_schema_version=...&input_sha256=...`  
3) if hit, reuse output artifact hash  
4) else execute stage, store output artifact, record cache entry + lineage edges

This is how you get replay, diffability, and targeted regeneration without relying on LLM determinism.
