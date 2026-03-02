from __future__ import annotations

import base64
from fastapi import FastAPI, HTTPException, Response

from .models import ArtifactCreate, EdgeCreate, CacheRecord, RegenerateRequest
from . import store
from . import planner

app = FastAPI(title="DADI Gateway", version="0.1.0")

@app.get("/health")
def health():
    return {"ok": True}

# Artifacts
@app.post("/artifacts")
def post_artifact(meta: ArtifactCreate, content_b64: str):
    try:
        content = base64.b64decode(content_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 content")
    rec = store.put_artifact(meta, content)
    return rec

@app.get("/artifacts/{sha256}")
def get_artifact(sha256: str):
    rec = store.get_artifact_meta(sha256)
    if not rec:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return rec

@app.get("/artifacts/{sha256}/content")
def get_artifact_content(sha256: str):
    content = store.get_artifact_content(sha256)
    if content is None:
        raise HTTPException(status_code=404, detail="Artifact content not available")
    return Response(content=content, media_type="application/octet-stream")

# Lineage edges
@app.post("/edges")
def post_edge(edge: EdgeCreate):
    store.record_edge(edge.from_sha256, edge.to_sha256, edge.edge_type, edge.stage_run_id)
    return {"ok": True}

@app.get("/lineage/{sha256}/upstream")
def get_upstream(sha256: str):
    return {"edges": store.lineage_upstream(sha256)}

@app.get("/lineage/{sha256}/downstream")
def get_downstream(sha256: str):
    return {"edges": store.lineage_downstream(sha256)}

# Cache
@app.get("/cache/lookup")
def cache_lookup(stage_name: str, stage_schema_version: str, input_sha256: str):
    out = store.cache_lookup(stage_name, stage_schema_version, input_sha256)
    if out is None:
        return {"hit": False}
    return {"hit": True, "output_sha256": out}

@app.post("/cache/record")
def cache_record(rec: CacheRecord):
    store.cache_record(rec.stage_name, rec.stage_schema_version, rec.input_sha256, rec.output_sha256)
    return {"ok": True}

# Plans
@app.post("/plan/regenerate")
def plan_regenerate(req: RegenerateRequest):
    try:
        return planner.create_plan(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/plan/{plan_id}")
def plan_get(plan_id: str):
    try:
        return planner.get_plan(plan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Plan not found")

@app.get("/plan/{plan_id}/explain")
def plan_explain(plan_id: str):
    try:
        return planner.explain_plan(plan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Plan not found")

@app.post("/execute/plan")
def plan_execute(payload: dict):
    plan_id = payload.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="Missing plan_id")
    planner.mark_executed(plan_id)
    return {"ok": True, "plan_id": plan_id, "status": "executed"}
