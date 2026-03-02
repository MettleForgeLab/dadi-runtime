from __future__ import annotations

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, constr

Sha256 = constr(pattern=r"^[a-fA-F0-9]{64}$")

class RegenerateRequest(BaseModel):
    old_prompt_sha256: Optional[Sha256] = None
    new_prompt_sha256: Optional[Sha256] = None
    old_toolchain_sha256: Optional[Sha256] = None
    new_toolchain_sha256: Optional[Sha256] = None

    pipeline_id: Optional[str] = None
    # Optional scoping filters (left minimal)
    created_after: Optional[str] = None
    created_before: Optional[str] = None

class PlanItem(BaseModel):
    pipeline_run_id: str
    start_stage_index: int
    reason: Literal["prompt_change","toolchain_change","mixed_change"]
    affected_stage_runs: int

    # New: execution guidance
    reuse_stages: List[int] = []
    recompute_stages: List[int] = []

    # New: pointers to currently materialized stage outputs (if present)
    # Example: {"3": "<sha256>", "4": "<sha256>"}
    current_stage_outputs: Dict[str, Sha256] = {}


class RegenerationPlan(BaseModel):
    plan_id: str
    status: Literal["planned","executed","cancelled"]
    request: Dict[str, Any]
    items: List[PlanItem]
