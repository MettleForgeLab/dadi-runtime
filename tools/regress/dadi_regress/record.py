from __future__ import annotations

import json
from typing import Dict, Any, Tuple, List

from .db import conn
from .hashing import sha256_hex

def _fetch_artifact_bytes(c, sha256: str) -> bytes:
    row = c.execute("SELECT content, storage_backend FROM artifacts WHERE sha256=%s", (sha256,)).fetchone()
    if not row:
        raise KeyError(f"Artifact not found: {sha256}")
    content, backend = row
    if backend != "postgres" or content is None:
        raise RuntimeError(f"Artifact content not available in postgres backend: {sha256}")
    return content

def record_fixture(pipeline_run_id: str) -> Tuple[Dict[str, Any], Dict[str, bytes]]:
    """Capture a fixture for a pipeline_run_id.

    Captures:
    - docpack artifact (from document_versions if present, else inferred from stage inputs)
    - all stage input/output artifacts referenced by stage_runs
    - prompt/toolchain hashes as pointers in manifest
    """
    artifacts: Dict[str, bytes] = {}

    with conn() as c:
        # Get stage runs in order
        sr_rows = c.execute(
            "SELECT stage_index, stage_name, stage_schema_version, toolchain_manifest_sha256, prompt_bundle_sha256, "
            "input_artifact_sha256, output_artifact_sha256, status "
            "FROM stage_runs WHERE pipeline_run_id=%s ORDER BY stage_index ASC",
            (pipeline_run_id,),
        ).fetchall()

        if not sr_rows:
            raise KeyError("No stage_runs found for pipeline_run_id")

        # Infer docpack from first stage input artifact content (stage_input-v1)
        first_input_sha = sr_rows[0][5]
        first_input_bytes = _fetch_artifact_bytes(c, first_input_sha)
        artifacts[first_input_sha] = first_input_bytes
        first_input = json.loads(first_input_bytes.decode("utf-8"))
        docpack_sha = first_input.get("docpack_sha256")
        if not docpack_sha:
            raise RuntimeError("Unable to infer docpack_sha256 from first stage input artifact")

        # Fetch docpack bytes
        docpack_bytes = _fetch_artifact_bytes(c, docpack_sha)
        artifacts[docpack_sha] = docpack_bytes

        stage_boundaries = []
        toolchains = set()
        prompts = set()

        for (stage_index, stage_name, stage_schema_version, toolchain_sha, prompt_sha, in_sha, out_sha, status) in sr_rows:
            toolchains.add(toolchain_sha)
            if prompt_sha:
                prompts.add(prompt_sha)

            in_bytes = artifacts.get(in_sha) or _fetch_artifact_bytes(c, in_sha)
            artifacts[in_sha] = in_bytes

            out_entry = None
            if out_sha:
                out_bytes = artifacts.get(out_sha) or _fetch_artifact_bytes(c, out_sha)
                artifacts[out_sha] = out_bytes
                out_entry = out_sha

            stage_boundaries.append({
                "stage_index": int(stage_index),
                "stage_name": stage_name,
                "stage_schema_version": stage_schema_version,
                "status": status,
                "toolchain_manifest_sha256": toolchain_sha,
                "prompt_bundle_sha256": prompt_sha,
                "input_sha256": in_sha,
                "output_sha256": out_entry
            })

        # Fetch prompt/toolchain artifact bytes if present in artifacts table
        for sha in toolchains.union(prompts):
            if not sha:
                continue
            try:
                b = _fetch_artifact_bytes(c, sha)
            except Exception:
                # Toolchain/prompt artifacts might not be stored as artifacts in some deployments; pointer-only is fine.
                continue
            artifacts[sha] = b

    # Manifest includes expected sha256 for each artifact file (self-verifying)
    artifact_meta = {}
    for sha, b in artifacts.items():
        artifact_meta[sha] = {
            "byte_length": len(b),
            "sha256": sha256_hex(b)
        }

    manifest = {
        "fixture_version": "fixture_manifest-v1",
        "pipeline_run_id": pipeline_run_id,
        "captured_at_utc": None,
        "docpack_sha256": docpack_sha,
        "artifacts": artifact_meta,
        "stage_boundaries": stage_boundaries
    }
    return manifest, artifacts
