# Stage 06 — Deterministic Rendering (DOCX-first)

## Inputs

- `report_model-v1` (canonical JSON)
- `render_input-v1` (canonical JSON):
  - report_model_sha256
  - template_sha256 (DOCX bytes)
  - render_params: { format: "docx", style: "<style_name>" }
  - toolchain_manifest_sha256

Templates are treated as artifacts:
- The template bytes are hash-identified.
- A template change results in a new render output artifact.

## Outputs

- `report/render/docx-v1` (DOCX bytes)

## Fail-closed

Rendering failures should:
- produce no render output artifact
- emit a deterministic error artifact at the orchestrator boundary

This module raises exceptions; the orchestrator should handle fail-closed error emission.
