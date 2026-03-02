from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Request

from .db import conn_with_tenant

router = APIRouter(tags=["runs"])

def tenant_id(request: Request) -> str:
    t = getattr(request.state, "tenant_id", None)
    if not t:
        raise HTTPException(status_code=401, detail="Unauthorized: tenant context not established")
    return t

def _stage_map(rows: List[tuple]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        (
            stage_index,
            stage_name,
            stage_schema_version,
            toolchain_manifest_sha256,
            prompt_bundle_sha256,
            input_artifact_sha256,
            output_artifact_sha256,
            status,
            fail_closed,
            deterministic_error_artifact_sha256,
        ) = r
        out[int(stage_index)] = {
            "stage_index": int(stage_index),
            "stage_name": stage_name,
            "stage_schema_version": stage_schema_version,
            "toolchain_manifest_sha256": toolchain_manifest_sha256,
            "prompt_bundle_sha256": prompt_bundle_sha256,
            "input_artifact_sha256": input_artifact_sha256,
            "output_artifact_sha256": output_artifact_sha256,
            "status": status,
            "fail_closed": bool(fail_closed),
            "deterministic_error_artifact_sha256": deterministic_error_artifact_sha256,
        }
    return out

@router.get("/runs/diff")
def diff_runs(request: Request, run_a: str, run_b: str) -> Dict[str, Any]:
    t = tenant_id(request)

    with conn_with_tenant(t) as c:
        ra = c.execute(
            "SELECT pipeline_run_id, pipeline_id, status FROM pipeline_runs WHERE tenant_id=%s AND pipeline_run_id=%s",
            (t, run_a),
        ).fetchone()
        rb = c.execute(
            "SELECT pipeline_run_id, pipeline_id, status FROM pipeline_runs WHERE tenant_id=%s AND pipeline_run_id=%s",
            (t, run_b),
        ).fetchone()
        if not ra or not rb:
            raise HTTPException(status_code=404, detail="One or both runs not found")

        rows_a = c.execute(
            "SELECT stage_index, stage_name, stage_schema_version, toolchain_manifest_sha256, prompt_bundle_sha256, "
            "input_artifact_sha256, output_artifact_sha256, status, fail_closed, deterministic_error_artifact_sha256 "
            "FROM stage_runs WHERE tenant_id=%s AND pipeline_run_id=%s ORDER BY stage_index ASC",
            (t, run_a),
        ).fetchall()

        rows_b = c.execute(
            "SELECT stage_index, stage_name, stage_schema_version, toolchain_manifest_sha256, prompt_bundle_sha256, "
            "input_artifact_sha256, output_artifact_sha256, status, fail_closed, deterministic_error_artifact_sha256 "
            "FROM stage_runs WHERE tenant_id=%s AND pipeline_run_id=%s ORDER BY stage_index ASC",
            (t, run_b),
        ).fetchall()

    ma = _stage_map(rows_a)
    mb = _stage_map(rows_b)

    all_indices = sorted(set(ma.keys()) | set(mb.keys()))
    comparisons: List[Dict[str, Any]] = []
    first_diff: Optional[int] = None
    classification: Optional[str] = None

    for i in all_indices:
        sa = ma.get(i)
        sb = mb.get(i)
        if sa is None:
            comparisons.append({"stage_index": i, "kind": "added_in_b", "a": None, "b": sb})
            if first_diff is None:
                first_diff = i
                classification = "structure"
            continue
        if sb is None:
            comparisons.append({"stage_index": i, "kind": "removed_in_b", "a": sa, "b": None})
            if first_diff is None:
                first_diff = i
                classification = "structure"
            continue

        same_output = sa["output_artifact_sha256"] == sb["output_artifact_sha256"]
        same_prompt = sa["prompt_bundle_sha256"] == sb["prompt_bundle_sha256"]
        same_toolchain = sa["toolchain_manifest_sha256"] == sb["toolchain_manifest_sha256"]

        kind = "same" if (same_output and same_prompt and same_toolchain) else "diff"
        if kind == "diff" and first_diff is None:
            first_diff = i
            if not same_output:
                if (not same_prompt) and (not same_toolchain):
                    classification = "output_prompt_toolchain"
                elif not same_prompt:
                    classification = "output_prompt"
                elif not same_toolchain:
                    classification = "output_toolchain"
                else:
                    classification = "output"
            else:
                if not same_prompt and same_toolchain:
                    classification = "prompt"
                elif same_prompt and not same_toolchain:
                    classification = "toolchain"
                else:
                    classification = "metadata"

        comparisons.append({
            "stage_index": i,
            "kind": kind,
            "a": sa,
            "b": sb,
            "same_output": same_output,
            "same_prompt": same_prompt,
            "same_toolchain": same_toolchain,
        })

    return {
        "tenant_id": t,
        "run_a": {"pipeline_run_id": run_a, "pipeline_id": str(ra[1]), "status": ra[2]},
        "run_b": {"pipeline_run_id": run_b, "pipeline_id": str(rb[1]), "status": rb[2]},
        "first_diff_stage_index": first_diff,
        "classification": classification,
        "comparisons": comparisons,
    }
