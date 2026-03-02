from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .models import RegenerateRequest
from .planner import plan_regeneration, get_plan, mark_executed, get_plan_explain

app = FastAPI(title="DADI Regeneration Planner", version="0.1.0")

@app.post("/plan/regenerate")
def post_plan(req: RegenerateRequest):
    try:
        plan = plan_regeneration(req)
        return plan.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/plan/{plan_id}")
def get_plan_endpoint(plan_id: str):
    try:
        plan = get_plan(plan_id)
        return plan.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Plan not found")


@app.get("/plan/{plan_id}/explain")
def explain_plan_endpoint(plan_id: str):
    try:
        return get_plan_explain(plan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Plan not found")

@app.post("/execute/plan")
def execute_plan(req: dict):
    # Minimal: expects {"plan_id": "..."}; execution remains manual by default.
    plan_id = req.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="Missing plan_id")
    mark_executed(plan_id)
    return {"ok": True, "plan_id": plan_id, "status": "executed"}
