from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from .db import conn_with_tenant

REF_TYPES = ("toolchain", "prompt", "input", "output", "error")

def expected_stage_runs_v1_artifacts(tenant: str, pipeline_run_id: str) -> Set[str]:
    with conn_with_tenant(tenant) as c:
        rows = c.execute(
            "SELECT toolchain_manifest_sha256, prompt_bundle_sha256, input_artifact_sha256, output_artifact_sha256, deterministic_error_artifact_sha256 "
            "FROM stage_runs WHERE tenant_id=%s AND pipeline_run_id=%s",
            (tenant, pipeline_run_id),
        ).fetchall()

    s: Set[str] = set()
    for tool_sha, prompt_sha, in_sha, out_sha, err_sha in rows:
        if tool_sha: s.add(tool_sha)
        if prompt_sha: s.add(prompt_sha)
        if in_sha: s.add(in_sha)
        if out_sha: s.add(out_sha)
        if err_sha: s.add(err_sha)
    return s

def expected_stage_runs_v1_sources(tenant: str, pipeline_run_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Return mapping sha256 -> list of source references in stage_runs."""
    with conn_with_tenant(tenant) as c:
        rows = c.execute(
            "SELECT stage_run_id, stage_index, stage_name, "
            "toolchain_manifest_sha256, prompt_bundle_sha256, input_artifact_sha256, output_artifact_sha256, deterministic_error_artifact_sha256 "
            "FROM stage_runs WHERE tenant_id=%s AND pipeline_run_id=%s ORDER BY stage_index ASC",
            (tenant, pipeline_run_id),
        ).fetchall()

    src: Dict[str, List[Dict[str, Any]]] = {}

    def add(sha: str | None, ref_type: str, stage_run_id: str, stage_index: int, stage_name: str) -> None:
        if not sha:
            return
        src.setdefault(sha, []).append({
            "ref_type": ref_type,
            "stage_run_id": str(stage_run_id),
            "stage_index": int(stage_index),
            "stage_name": stage_name
        })

    for stage_run_id, stage_index, stage_name, tool_sha, prompt_sha, in_sha, out_sha, err_sha in rows:
        add(tool_sha, "toolchain", stage_run_id, stage_index, stage_name)
        add(prompt_sha, "prompt", stage_run_id, stage_index, stage_name)
        add(in_sha, "input", stage_run_id, stage_index, stage_name)
        add(out_sha, "output", stage_run_id, stage_index, stage_name)
        add(err_sha, "error", stage_run_id, stage_index, stage_name)

    return src

def verify_closure_stage_runs_v1(manifest: Dict[str, Any], expected: Set[str]) -> Dict[str, Any]:
    listed: Set[str] = set()
    for a in manifest.get("artifacts", []) or []:
        if isinstance(a, dict) and isinstance(a.get("sha256"), str):
            listed.add(a["sha256"])

    missing = sorted(list(expected - listed))
    extra = sorted(list(listed - expected))

    return {
        "ok": len(missing) == 0,
        "missing_expected_artifacts": missing,
        "extra_manifest_artifacts": extra,
    }
