"""DADI Validator Pack (jsonschema)

- Loads Draft 2020-12 JSON Schemas from ./schemas/
- Validates artifacts by schema_version (fail-closed)
- Produces deterministic error records (stable JSON)
- Canonicalizes JSON and computes SHA256 (for canonical formats)

This is infrastructure glue: validation + hashing.
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for


def canonical_json_bytes(obj: Any) -> bytes:
    """    Canonical-ish JSON encoding:
    - UTF-8
    - sort_keys=True
    - separators for stable whitespace

    NOTE: Deterministic array ordering is semantic; this function does not reorder arrays.
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    schema_version: str
    sha256: Optional[str]
    canonical_bytes: Optional[bytes]
    error_record: Optional[Dict[str, Any]]


class SchemaRegistry:
    """Loads schemas and validates documents by schema_version."""

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
            schema_file = os.path.join(self.schemas_path, filename)
            with open(schema_file, "r", encoding="utf-8") as f:
                schema = json.load(f)
            self._schemas[schema_version] = schema

            V = validator_for(schema)
            V.check_schema(schema)
            self._validators[schema_version] = Draft202012Validator(schema)

    def available(self) -> List[str]:
        return sorted(self._schemas.keys())

    def get_schema(self, schema_version: str) -> Dict[str, Any]:
        return self._schemas[schema_version]

    def validate(self, artifact: Dict[str, Any]) -> ValidationResult:
        """        Fail-closed validation by artifact['schema_version'].

        Returns:
          - ok=True with canonical_bytes and sha256
          - ok=False with deterministic error_record (canonicalizable JSON)
        """
        sv = artifact.get("schema_version")
        if not isinstance(sv, str) or not sv:
            err = self._error_record(
                schema_version="(missing)",
                error_code="missing_schema_version",
                message="Artifact is missing required string field: schema_version",
                errors=[],
            )
            return ValidationResult(False, "(missing)", None, None, err)

        if sv not in self._validators:
            err = self._error_record(
                schema_version=sv,
                error_code="unknown_schema_version",
                message="No schema registered for schema_version",
                errors=[{"path": ["schema_version"], "message": f"Unknown schema_version: {sv}"}],
            )
            return ValidationResult(False, sv, None, None, err)

        validator = self._validators[sv]
        errors = sorted(validator.iter_errors(artifact), key=lambda e: (list(e.path), e.message))

        if errors:
            compact = []
            for e in errors:
                compact.append(
                    {
                        "path": list(e.path),
                        "schema_path": list(e.schema_path),
                        "message": e.message,
                    }
                )
            err = self._error_record(
                schema_version=sv,
                error_code="schema_validation_failed",
                message="Artifact failed JSON Schema validation",
                errors=compact,
            )
            return ValidationResult(False, sv, None, None, err)

        b = canonical_json_bytes(artifact)
        h = sha256_hex(b)
        return ValidationResult(True, sv, h, b, None)

    @staticmethod
    def _error_record(schema_version: str, error_code: str, message: str, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """        Deterministic error record:
        - no timestamps
        - stable key ordering when canonicalized
        """
        return {
            "schema_version": "validation_error-v1",
            "target_schema_version": schema_version,
            "error_code": error_code,
            "message": message,
            "errors": errors,
        }


def validate_and_hash(registry: SchemaRegistry, artifact: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """    Convenience wrapper.

    Returns:
      ok, sha256_or_error_sha256, artifact_or_error_record
    """
    res = registry.validate(artifact)
    if res.ok and res.sha256 and res.canonical_bytes:
        return True, res.sha256, artifact
    assert res.error_record is not None
    err_bytes = canonical_json_bytes(res.error_record)
    err_sha = sha256_hex(err_bytes)
    return False, err_sha, res.error_record
