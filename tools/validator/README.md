# DADI Validator Pack (jsonschema)

This pack contains Draft 2020-12 JSON Schemas and a small Python validator that supports **fail-closed** artifact validation.

## Contents

- `schemas/` — JSON Schemas (Draft 2020-12)
  - `index.json` maps `schema_version` → schema filename
- `validator.py` — schema registry + deterministic validation error records + canonical JSON hashing
- `app.py` — minimal FastAPI example using the validator

## Install

```bash
pip install jsonschema fastapi uvicorn pydantic
```

## Validate an artifact (Python)

```python
from validator import SchemaRegistry, validate_and_hash
import os

registry = SchemaRegistry(os.path.join(os.getcwd(), "schemas"))

artifact = {
  "schema_version": "stage02-output-v1",
  "stage": {"index": 2, "name": "02_classify", "schema_version": "v1"},
  "results": {
    "doc_profile": {"doc_types": ["pitch_deck"], "confidence": 0.9},
    "section_map": [],
    "content_index": {"tables": [], "figures": [], "key_blocks": []},
    "extraction_plan": {"targets": ["revenue"], "priority": [{"target":"revenue","importance":"high"}]}
  },
  "citations": [],
  "provenance": {"input_sha256": "0"*64, "prompt_bundle_sha256": "1"*64}
}

ok, sha_or_err_sha, out = validate_and_hash(registry, artifact)
print(ok, sha_or_err_sha)
```

## FastAPI example

```bash
uvicorn app:app --reload
```

- `GET /schemas`
- `POST /validate` with `{"artifact": {...}}`

## Deterministic error records

On failure, `validator.py` returns a stable error object:

- `schema_version`: `validation_error-v1`
- `target_schema_version`
- `error_code`
- `message`
- `errors[]`: list of `{path, schema_path, message}`

No timestamps are included in error artifacts to preserve deterministic hashing.
