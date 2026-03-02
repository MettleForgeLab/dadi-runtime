# DADI DOCX Renderer (DOCX-first)

This pack implements a DOCX-first rendering stage suitable for Stage 06:

- Input: `render_input-v1` (canonical JSON) referencing:
  - `report_model_sha256`
  - `template_sha256`
  - `toolchain_manifest_sha256`
  - `render_params` (`format: docx`, `style: ...`)
- Output: a rendered DOCX artifact (`report/render/docx-v1`)

## Determinism boundary

DOCX output determinism is defined relative to:
- the declared toolchain (python-docx version, runtime)
- the template bytes (hash-identified)
- the render_input parameters
- the report_model bytes (hash-identified)

This module does not claim universal reproducibility across different toolchains.

## What it does

- Loads the report model (`report_model-v1`) from the artifact store.
- Loads a DOCX template from the artifact store (optional; required by render_input).
- Renders:
  - Title
  - Summary blocks
  - Sections and blocks (paragraph/bullet/table)
- Emits a DOCX byte artifact.
- Fails closed by raising an exception (expected to be caught by orchestrator, producing deterministic error artifact).

## Files

- `dadi_renderer/store.py` — tenant-less store adapter (uses artifacts table)
- `dadi_renderer/render_docx.py` — deterministic renderer
- `dadi_renderer/stage06_handler.py` — orchestrator-compatible handler

## Usage

See `examples/render_from_db.py` for a minimal run (requires `DATABASE_URL` and existing artifacts in Postgres).
