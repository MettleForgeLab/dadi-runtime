from __future__ import annotations

import json
import os
from typing import Dict, Any, List, Tuple

from .fixture import load_fixture
from .hashing import sha256_hex
from .schema_registry import SchemaRegistry

def verify_fixture(fixture_path: str, schemas_path: str | None = None) -> Dict[str, Any]:
    fx = load_fixture(fixture_path)
    manifest = fx.manifest
    artifacts_dir = os.path.join(fx.root, "artifacts")

    results = {
        "ok": True,
        "missing_files": [],
        "hash_mismatches": [],
        "schema_failures": []
    }

    # Verify artifact files exist + hashes match
    for sha, meta in manifest.get("artifacts", {}).items():
        p = os.path.join(artifacts_dir, sha)
        if not os.path.exists(p):
            results["ok"] = False
            results["missing_files"].append(sha)
            continue
        b = open(p, "rb").read()
        h = sha256_hex(b)
        if h != sha or h != meta.get("sha256"):
            results["ok"] = False
            results["hash_mismatches"].append({"sha": sha, "expected": sha, "computed": h})

    # Optional schema validation for JSON artifacts
    if schemas_path:
        reg = SchemaRegistry(schemas_path)
        for sha in manifest.get("artifacts", {}).keys():
            p = os.path.join(artifacts_dir, sha)
            if not os.path.exists(p):
                continue
            b = open(p, "rb").read()
            # Attempt JSON parse; skip non-JSON
            try:
                obj = json.loads(b.decode("utf-8"))
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            res = reg.validate(obj)
            if not res.ok:
                results["ok"] = False
                results["schema_failures"].append({
                    "sha": sha,
                    "schema_version": obj.get("schema_version"),
                    "error": res.error_record
                })

    return results
