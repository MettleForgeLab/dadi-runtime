# DADI Regression Harness

This pack provides a deterministic regression harness for multi-stage pipelines that produce canonical artifacts.

It supports:

- **record**: capture a pipeline run into a fixture pack (artifacts + manifest)
- **verify**: verify fixture integrity (hashes + schema validation)
- **diff** (optional): compare two fixture manifests to localize first drift boundary

The harness is intentionally minimal: pure Python + Postgres + JSON Schema validation.

## Fixture format

A fixture pack is a directory or zip with:

- `fixture_manifest.json`
- `artifacts/<sha256>` (raw bytes, one file per artifact hash)

The manifest includes:
- fixture metadata
- the set of included artifact hashes
- expected SHA256 of each artifact file (self-verifying)
- selected boundary pointers (docpack, per-stage input/output, prompt/toolchain)

## Install

```bash
pip install -e .
```

## Commands

Record a fixture from a pipeline run:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/dadi"
python -m dadi_regress.cli record --pipeline-run-id <UUID> --out fixture.zip
```

Verify a fixture:

```bash
python -m dadi_regress.cli verify --fixture fixture.zip
```

Diff two fixtures:

```bash
python -m dadi_regress.cli diff --a fixture_old.zip --b fixture_new.zip
```

## Notes

- This harness does not re-execute your pipeline by default. It focuses on **capturing** and **verifying** deterministic state.
- To add execution-based regression (rerun + compare), wire this harness to your orchestrator and LLM capture adapter.
