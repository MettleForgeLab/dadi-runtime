from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict, List

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for

def _schemas_root() -> str:
    # In monorepo, schemas live at ../../schemas relative to dadi_gateway package.
    here = os.path.dirname(__file__)
    # services/gateway/dadi_gateway -> services/gateway/dadi_gateway/../../.. -> repo root? We'll search upward for 'schemas/index.json'
    cand = os.path.abspath(os.path.join(here, "..", "..", "..", "schemas"))
    return cand

@lru_cache(maxsize=1)
def _load_manifest_validator() -> Draft202012Validator:
    root = _schemas_root()
    schema_path = os.path.join(root, "deliverable_manifest-v1.schema.json")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    V = validator_for(schema)
    V.check_schema(schema)
    return Draft202012Validator(schema)

def validate_deliverable_manifest(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    v = _load_manifest_validator()
    errors = sorted(v.iter_errors(manifest), key=lambda e: (list(e.path), e.message))
    out = []
    for e in errors:
        out.append({"path": list(e.path), "schema_path": list(e.schema_path), "message": e.message})
    return out
