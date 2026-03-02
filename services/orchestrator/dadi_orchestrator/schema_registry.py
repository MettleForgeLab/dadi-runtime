from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for

from .hashing import canonical_json_bytes, sha256_hex

@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    schema_version: str
    sha256: Optional[str]
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
        for schema_version, filename in self._index.items():
            p = os.path.join(self.schemas_path, filename)
            with open(p, "r", encoding="utf-8") as f:
                schema = json.load(f)
            V = validator_for(schema)
            V.check_schema(schema)
            self._schemas[schema_version] = schema
            self._validators[schema_version] = Draft202012Validator(schema)

    def available(self) -> List[str]:
        return sorted(self._schemas.keys())

    def validate(self, artifact: Dict[str, Any]) -> ValidationResult:
        sv = artifact.get("schema_version")
        if not isinstance(sv, str) or not sv:
            err = self._error_record("(missing)", "missing_schema_version", "Missing required string field: schema_version", [])
            return ValidationResult(False, "(missing)", None, err)

        if sv not in self._validators:
            err = self._error_record(sv, "unknown_schema_version", "No schema registered for schema_version",
                                     [{"path":["schema_version"],"message":f"Unknown schema_version: {sv}"}])
            return ValidationResult(False, sv, None, err)

        validator = self._validators[sv]
        errs = sorted(validator.iter_errors(artifact), key=lambda e: (list(e.path), e.message))
        if errs:
            compact = [{"path":list(e.path), "schema_path":list(e.schema_path), "message":e.message} for e in errs]
            err = self._error_record(sv, "schema_validation_failed", "Artifact failed JSON Schema validation", compact)
            return ValidationResult(False, sv, None, err)

        b = canonical_json_bytes(artifact)
        return ValidationResult(True, sv, sha256_hex(b), None)

    @staticmethod
    def _error_record(target_sv: str, error_code: str, message: str, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "schema_version": "validation_error-v1",
            "target_schema_version": target_sv,
            "error_code": error_code,
            "message": message,
            "errors": errors
        }

def validate_or_error_artifact(registry: SchemaRegistry, artifact: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any]]:
    res = registry.validate(artifact)
    if res.ok and res.sha256:
        return True, res.sha256, artifact
    assert res.error_record is not None
    err_sha = sha256_hex(canonical_json_bytes(res.error_record))
    return False, err_sha, res.error_record
