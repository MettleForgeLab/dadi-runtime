"""FastAPI integration example (minimal)

pip install fastapi uvicorn jsonschema pydantic

Run:
  uvicorn app:app --reload
"""
from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from validator import SchemaRegistry, validate_and_hash

SCHEMAS_PATH = os.path.join(os.path.dirname(__file__), "schemas")
registry = SchemaRegistry(SCHEMAS_PATH)

app = FastAPI(title="DADI Validator API", version="0.1")

class Payload(BaseModel):
    artifact: Dict[str, Any]

@app.get("/schemas")
def list_schemas():
    return {"available_schema_versions": registry.available()}

@app.post("/validate")
def validate(payload: Payload):
    ok, sha, out = validate_and_hash(registry, payload.artifact)
    if not ok:
        raise HTTPException(status_code=422, detail={"error_sha256": sha, "error": out})
    return {"ok": True, "artifact_sha256": sha}
