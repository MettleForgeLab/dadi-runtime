from __future__ import annotations

import uuid
import json
from typing import Any, Dict, List

from .db import conn_with_tenant, tx_with_tenant
from .models import RegenerateRequest

def _det_reason(prompt_hit: bool, toolchain_hit: bool) -> str:
    if prompt_hit and toolchain_hit:
        return "mixed_change"
    if prompt_hit:
        return "prompt_change"
    return "toolchain_change"

def create_plan(tenant_id: str, req: RegenerateRequest) -> Dict[str, Any]:
    if not ((req.old_prompt_sha256 and req.new_prompt_sha256) or (req.old_toolchain_sha256 and req.new_toolchain_sha256)):
        raise ValueError("Must provide either old/new prompt SHA256 or old/new toolchain SHA256 (or both).")

    plan_id = str(uuid.uuid4())

    where = ["sr.tenant_id = %s", "pr.tenant_id = %s"]
    params: List[Any] = [tenant_id, tenant_id]

    if req.pipeline_id:
        where.append("pr.pipeline_id = %s")
        params.append(req.pipeline_id)
    if req.created_after:
        where.append("pr.created_at >= %s")
        params.append(req.created_after)
    if req.created_before:
        where.append("pr.created_at <= %s")
        params.append(req.created_before)

    sr_match = []
    if req.old_prompt_sha256:
        sr_match.append("sr.prompt_bundle_sha256 = %s")
        params.append(req.old_prompt_sha256)
    if req.old_toolchain_sha256:
        sr_match.append("sr.toolchain_manifest_sha256 = %s")
        params.append(req.old_toolchain_sha256)

    prompt_cmp = req.old_prompt_sha256 or ("0"*64)
    toolchain_cmp = req.old_toolchain_sha256 or ("0"*64)

    q = f"""
    SELECT
      sr.pipeline_run_id,
      MIN(sr.stage_index) AS min_stage_index,
      SUM(CASE WHEN sr.prompt_bundle_sha256 = %s THEN 1 ELSE 0 END) AS prompt_hits,
      SUM(CASE WHEN sr.toolchain_manifest_sha256 = %s THEN 1 ELSE 0 END) AS toolchain_hits,
      COUNT(*) AS affected_stage_runs
    FROM stage_runs sr
    JOIN pipeline_runs pr ON pr.pipeline_run_id = sr.pipeline_run_id
    WHERE ({' OR '.join(sr_match)}) AND ({' AND '.join(where)})
    GROUP BY sr.pipeline_run_id
    ORDER BY sr.pipeline_run_id ASC
    """

    with conn_with_tenant(tenant_id) as c:
        rows = c.execute(q, [prompt_cmp, toolchain_cmp] + params).fetchall()

    items = []
    for r in rows:
        pipeline_run_id, min_stage_index, prompt_hits, toolchain_hits, affected_count = r

        with conn_with_tenant(tenant_id) as c:
            sr_rows = c.execute(
                "SELECT stage_index, output_artifact_sha256, status "
                "FROM stage_runs WHERE tenant_id=%s AND pipeline_run_id=%s ORDER BY stage_index ASC",
                (tenant_id, pipeline_run_id),
            ).fetchall()

        existing_indices = [int(x[0]) for x in sr_rows]
        max_index = max(existing_indices) if existing_indices else int(min_stage_index)

        reuse_stages = []
        current_outputs = {}
        for stage_index, out_sha, status in sr_rows:
            if out_sha and status == "success":
                current_outputs[str(int(stage_index))] = out_sha
            if int(stage_index) < int(min_stage_index) and status == "success" and out_sha:
                reuse_stages.append(int(stage_index))

        start_idx = int(min_stage_index)
        recompute_stages = list(range(start_idx, max_index + 1))

        reason = _det_reason(prompt_hits > 0, toolchain_hits > 0)
        items.append({
            "pipeline_run_id": str(pipeline_run_id),
            "start_stage_index": start_idx,
            "reason": reason,
            "affected_stage_runs": int(affected_count),
            "reuse_stages": reuse_stages,
            "recompute_stages": recompute_stages,
            "current_stage_outputs": current_outputs,
        })

    plan_json = {
        "plan_id": plan_id,
        "tenant_id": tenant_id,
        "status": "planned",
        "request": req.model_dump(),
        "items": items,
    }

    with tx_with_tenant(tenant_id) as c:
        c.execute(
            "INSERT INTO regeneration_plans (tenant_id, plan_id, status, request_json, plan_json) VALUES (%s,%s,'planned',%s::jsonb,%s::jsonb)",
            (tenant_id, plan_id, req.model_dump_json(), json.dumps(plan_json)),
        )

    return plan_json

def get_plan(tenant_id: str, plan_id: str) -> Dict[str, Any]:
    with conn_with_tenant(tenant_id) as c:
        row = c.execute("SELECT status, plan_json FROM regeneration_plans WHERE tenant_id=%s AND plan_id=%s", (tenant_id, plan_id)).fetchone()
    if not row:
        raise KeyError("Plan not found")
    status, plan_json = row
    data = plan_json if isinstance(plan_json, dict) else plan_json
    data["status"] = status
    return data

def explain_plan(tenant_id: str, plan_id: str) -> Dict[str, Any]:
    plan = get_plan(tenant_id, plan_id)
    req = plan.get("request", {})
    old_prompt = req.get("old_prompt_sha256")
    old_toolchain = req.get("old_toolchain_sha256")

    explain_items = []
    for item in plan.get("items", []):
        pipeline_run_id = item["pipeline_run_id"]
        with conn_with_tenant(tenant_id) as c:
            sr_rows = c.execute(
                "SELECT stage_run_id, stage_index, stage_name, stage_schema_version, "
                "prompt_bundle_sha256, toolchain_manifest_sha256, input_artifact_sha256, output_artifact_sha256, status "
                "FROM stage_runs WHERE tenant_id=%s AND pipeline_run_id=%s ORDER BY stage_index ASC",
                (tenant_id, pipeline_run_id),
            ).fetchall()

        matches = []
        for (stage_run_id, stage_index, stage_name, stage_schema_version,
             prompt_sha, toolchain_sha, input_sha, output_sha, status) in sr_rows:
            prompt_hit = bool(old_prompt and prompt_sha == old_prompt)
            toolchain_hit = bool(old_toolchain and toolchain_sha == old_toolchain)
            if prompt_hit or toolchain_hit:
                matches.append({
                    "stage_run_id": str(stage_run_id),
                    "stage_index": int(stage_index),
                    "stage_name": stage_name,
                    "stage_schema_version": stage_schema_version,
                    "status": status,
                    "prompt_bundle_sha256": prompt_sha,
                    "toolchain_manifest_sha256": toolchain_sha,
                    "input_artifact_sha256": input_sha,
                    "output_artifact_sha256": output_sha,
                    "prompt_hit": prompt_hit,
                    "toolchain_hit": toolchain_hit
                })

        explain_items.append({
            "pipeline_run_id": pipeline_run_id,
            "reason": item["reason"],
            "start_stage_index": item["start_stage_index"],
            "matches": matches,
            "earliest_match": matches[0] if matches else None
        })

    return {
        "plan_id": plan["plan_id"],
        "tenant_id": tenant_id,
        "status": plan["status"],
        "request": req,
        "explain_items": explain_items
    }

def mark_executed(tenant_id: str, plan_id: str) -> None:
    with tx_with_tenant(tenant_id) as c:
        c.execute("UPDATE regeneration_plans SET status='executed' WHERE tenant_id=%s AND plan_id=%s", (tenant_id, plan_id))
