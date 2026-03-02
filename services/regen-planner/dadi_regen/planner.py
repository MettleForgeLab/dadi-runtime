from __future__ import annotations

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .db import conn, tx
from .models import RegenerateRequest, RegenerationPlan, PlanItem

def _det_reason(prompt_hit: bool, toolchain_hit: bool) -> str:
    if prompt_hit and toolchain_hit:
        return "mixed_change"
    if prompt_hit:
        return "prompt_change"
    return "toolchain_change"

def plan_regeneration(req: RegenerateRequest) -> RegenerationPlan:
    # Basic sanity: require at least one change pair.
    if not ((req.old_prompt_sha256 and req.new_prompt_sha256) or (req.old_toolchain_sha256 and req.new_toolchain_sha256)):
        raise ValueError("Must provide either old/new prompt SHA256 or old/new toolchain SHA256 (or both).")

    plan_id = str(uuid.uuid4())

    # Build SQL WHERE clauses deterministically.
    where = []
    params: List[Any] = []

    if req.pipeline_id:
        where.append("pr.pipeline_id = %s")
        params.append(req.pipeline_id)

    # created_at filters if provided (ISO8601 strings expected)
    if req.created_after:
        where.append("pr.created_at >= %s")
        params.append(req.created_after)
    if req.created_before:
        where.append("pr.created_at <= %s")
        params.append(req.created_before)

    # Stage run match clauses
    sr_match = []
    if req.old_prompt_sha256:
        sr_match.append("sr.prompt_bundle_sha256 = %s")
        params.append(req.old_prompt_sha256)
    if req.old_toolchain_sha256:
        sr_match.append("sr.toolchain_manifest_sha256 = %s")
        params.append(req.old_toolchain_sha256)

    if not sr_match:
        raise ValueError("No match clause built; check request.")

    # Final query: find earliest stage_index per pipeline_run_id that used the old prompt/toolchain
    q = """
    SELECT
      sr.pipeline_run_id,
      MIN(sr.stage_index) AS min_stage_index,
      SUM(CASE WHEN sr.prompt_bundle_sha256 = %s THEN 1 ELSE 0 END) AS prompt_hits,
      SUM(CASE WHEN sr.toolchain_manifest_sha256 = %s THEN 1 ELSE 0 END) AS toolchain_hits,
      COUNT(*) AS affected_stage_runs
    FROM stage_runs sr
    JOIN pipeline_runs pr ON pr.pipeline_run_id = sr.pipeline_run_id
    WHERE ({sr_match})
      {pipeline_filters}
    GROUP BY sr.pipeline_run_id
    ORDER BY sr.pipeline_run_id ASC
    """

    # For the CASE comparisons we need placeholders even if old sha missing; use impossible value if absent.
    prompt_cmp = req.old_prompt_sha256 or ("0"*64)
    toolchain_cmp = req.old_toolchain_sha256 or ("0"*64)

    pipeline_filters = ""
    if where:
        pipeline_filters = " AND " + " AND ".join(where)

    q = q.format(
        sr_match=" OR ".join(sr_match),
        pipeline_filters=pipeline_filters
    )

    items: List[PlanItem] = []

    with conn() as c:
        rows = c.execute(q, [prompt_cmp, toolchain_cmp] + params).fetchall()

    for r in rows:
        pipeline_run_id, min_stage_index, prompt_hits, toolchain_hits, affected_count = r
        reason = _det_reason(prompt_hits > 0, toolchain_hits > 0)

        # Determine available stage indices and current output hashes for this run.
        with conn() as c:
            sr_rows = c.execute(
                "SELECT stage_index, output_artifact_sha256, status "
                "FROM stage_runs WHERE pipeline_run_id=%s ORDER BY stage_index ASC",
                (pipeline_run_id,),
            ).fetchall()

        existing_indices = [int(x[0]) for x in sr_rows]
        max_index = max(existing_indices) if existing_indices else int(min_stage_index)

        # Reuse stages are those < start index that have successful outputs.
        reuse_stages = []
        current_outputs = {}
        for stage_index, out_sha, status in sr_rows:
            if out_sha and status == "success":
                current_outputs[str(int(stage_index))] = out_sha
            if int(stage_index) < int(min_stage_index) and status == "success" and out_sha:
                reuse_stages.append(int(stage_index))

        start_idx = int(min_stage_index)
        recompute_stages = list(range(start_idx, max_index + 1))

        items.append(PlanItem(
            pipeline_run_id=str(pipeline_run_id),
            start_stage_index=start_idx,
            reason=reason,
            affected_stage_runs=int(affected_count),
            reuse_stages=reuse_stages,
            recompute_stages=recompute_stages,
            current_stage_outputs=current_outputs,
        ))

    plan = RegenerationPlan(
        plan_id=plan_id,
        status="planned",
        request=req.model_dump(),
        items=items,
    )

    # Persist plan deterministically (JSONB)
    with tx() as c:
        c.execute(
            "INSERT INTO regeneration_plans (plan_id, status, request_json, plan_json) VALUES (%s, 'planned', %s::jsonb, %s::jsonb)",
            (plan_id, req.model_dump_json(), plan.model_dump_json()),
        )

    return plan

def get_plan(plan_id: str) -> RegenerationPlan:
    with conn() as c:
        row = c.execute(
            "SELECT status, plan_json FROM regeneration_plans WHERE plan_id=%s",
            (plan_id,),
        ).fetchone()
    if not row:
        raise KeyError("Plan not found")
    status, plan_json = row
    data = plan_json if isinstance(plan_json, dict) else plan_json
    # Ensure status matches row status
    data["status"] = status
    return RegenerationPlan.model_validate(data)

def mark_executed(plan_id: str) -> None:
    with tx() as c:
        c.execute(
            "UPDATE regeneration_plans SET status='executed' WHERE plan_id=%s",
            (plan_id,),
        )


def get_plan_explain(plan_id: str) -> dict:
    """Return an explanation payload for a stored plan.

    Explanation includes, per pipeline_run_id:
    - earliest matching stage_run (by stage_index)
    - matching stage indices and their prompt/toolchain hashes
    - input/output artifact hashes for matching stages
    """
    plan = get_plan(plan_id)
    req = plan.request

    old_prompt = req.get("old_prompt_sha256")
    old_toolchain = req.get("old_toolchain_sha256")

    explain_items = []

    for item in plan.items:
        pipeline_run_id = item.pipeline_run_id

        match_rows = []
        with conn() as c:
            # Pull all stage_runs for the run; explain will mark which ones match the old hashes.
            sr_rows = c.execute(
                "SELECT stage_run_id, stage_index, stage_name, stage_schema_version, "
                "prompt_bundle_sha256, toolchain_manifest_sha256, input_artifact_sha256, output_artifact_sha256, status "
                "FROM stage_runs WHERE pipeline_run_id=%s ORDER BY stage_index ASC",
                (pipeline_run_id,),
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

        earliest = matches[0] if matches else None

        explain_items.append({
            "pipeline_run_id": pipeline_run_id,
            "reason": item.reason,
            "start_stage_index": item.start_stage_index,
            "matches": matches,
            "earliest_match": earliest
        })

    return {
        "plan_id": plan.plan_id,
        "status": plan.status,
        "request": req,
        "explain_items": explain_items
    }
