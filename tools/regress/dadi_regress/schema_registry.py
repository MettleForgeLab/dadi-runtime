from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for

from .hashing import canonical_json_bytes, sha256_hex

@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    schema_version: str
    error_record: Optional[Dict[str, Any]]

class SchemaRegistry:
    def __init__(self, schemas_path: str) -> None:
        self.schemas_path = schemas_path
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}
        self._index: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        index_path = os.path.join(self.schemas_path, "index.json")
        with open(index_path, "r", encoding="utf-8") as f:
            self._index = json.load(f)

        for sv, filename in self._index.items():
            p = os.path.join(self.schemas_path, filename)
            with open(p, "r", encoding="utf-8") as f:
                schema = json.load(f)
            V = validator_for(schema)
            V.check_schema(schema)
            self._schemas[sv] = schema
            self._validators[sv] = Draft202012Validator(schema)

    def validate(self, artifact: Dict[str, Any]) -> ValidationResult:
        sv = artifact.get("schema_version")
        if not isinstance(sv, str) or not sv:
            return ValidationResult(False, "(missing)", {
                "schema_version":"validation_error-v1",
                "target_schema_version":"(missing)",
                "error_code":"missing_schema_version",
                "message":"Missing required string field: schema_version",
                "errors":[]
            })
        if sv not in self._validators:
            return ValidationResult(False, sv, {
                "schema_version":"validation_error-v1",
                "target_schema_version":sv,
                "error_code":"unknown_schema_version",
                "message":"No schema registered for schema_version",
                "errors":[{"path":["schema_version"],"message":f"Unknown schema_version: {sv}"}]
            })
        v = self._validators[sv]
        errs = sorted(v.iter_errors(artifact), key=lambda e: (list(e.path), e.message))
        if errs:
            compact = [{"path":list(e.path),"schema_path":list(e.schema_path),"message":e.message} for e in errs]
            return ValidationResult(False, sv, {
                "schema_version":"validation_error-v1",
                "target_schema_version":sv,
                "error_code":"schema_validation_failed",
                "message":"Artifact failed JSON Schema validation",
                "errors":compact
            })
        return ValidationResult(True, sv, None)
