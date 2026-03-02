from __future__ import annotations

import base64
import os
from fastapi import FastAPI, HTTPException, Response, Request
from .streaming_utils import stream_bytes

from .models import ArtifactCreate, EdgeCreate, CacheRecord, RegenerateRequest
from . import store
from . import planner
from .jwt_auth import JWTAuthMiddleware, require_scope
from .auth_oidc import OIDCAuthMiddleware
from .deliverables_routes import router as deliverables_router
from .bundle_download_routes import router as bundle_download_router
from .revocation_routes import router as revocation_router
from .audit import router as audit_router
from .evidence_routes import router as evidence_router
from .health_extra import router as health_extra_router
from .compliance_health import router as compliance_health_router
from .bundles_routes import router as bundles_router
from .run_routes import router as run_router
from .diff_routes import router as diff_router

CONTENT_SCOPE = os.getenv("DADI_CONTENT_SCOPE", "artifact:read_bytes")

app = FastAPI(title="DADI Gateway (v0.2)", version="0.2.0")
import os
auth_mode = os.getenv('DADI_AUTH_MODE','off').strip().lower()
if auth_mode == 'oidc':
    app.add_middleware(OIDCAuthMiddleware)
else:
    app.add_middleware(JWTAuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RateLimitRedisMiddleware)
app.include_router(run_router)
app.include_router(deliverables_router)
app.include_router(bundle_download_router)
app.include_router(revocation_router)
app.include_router(audit_router)
app.include_router(evidence_router)
app.include_router(health_extra_router)
app.include_router(compliance_health_router)
app.include_router(bundles_router)
app.include_router(diff_router)

def tenant_id(request: Request) -> str:
    t = getattr(request.state, "tenant_id", None)
    if not t:
        raise HTTPException(status_code=401, detail="Unauthorized: tenant context not established")
    return t

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/artifacts")
def post_artifact(request: Request, meta: ArtifactCreate, content_b64: str):
    t = tenant_id(request)
    try:
        content = base64.b64decode(content_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 content")
    return store.put_artifact(t, meta, content)

@app.get("/artifacts/{sha256}")
def get_artifact(request: Request, sha256: str):
    t = tenant_id(request)
    rec = store.get_artifact_meta(t, sha256)
    if not rec:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return rec

@app.get("/artifacts/{sha256}/content")
def get_artifact_content(request: Request, sha256: str):
    # Gate bytes by scope
    deny = require_scope(request, CONTENT_SCOPE)
    if deny:
        return deny
    t = tenant_id(request)
    meta = store.get_artifact_meta(t, sha256)
    if meta and meta.get('artifact_type') in ('deliverable/bundle/zip-v1','deliverable/evidence/bundle-zip-v1'):
        raise HTTPException(status_code=403, detail='Direct bundle download is disabled. Use /deliverables/{deliverable_id}/bundles/{bundle_id}/download')

    content = store.get_artifact_content(t, sha256)
    if content is None:
        raise HTTPException(status_code=404, detail="Artifact content not available")
    return stream_bytes(content, content_type="application/octet-stream")

@app.post("/edges")
def post_edge(request: Request, edge: EdgeCreate):
    t = tenant_id(request)
    store.record_edge(t, edge.from_sha256, edge.to_sha256, edge.edge_type, edge.stage_run_id)
    return {"ok": True}

@app.get("/lineage/{sha256}/upstream")
def get_upstream(request: Request, sha256: str):
    t = tenant_id(request)
    return {"edges": store.lineage_upstream(t, sha256)}

@app.get("/lineage/{sha256}/downstream")
def get_downstream(request: Request, sha256: str):
    t = tenant_id(request)
    return {"edges": store.lineage_downstream(t, sha256)}

@app.get("/cache/lookup")
def cache_lookup(request: Request, stage_name: str, stage_schema_version: str, input_sha256: str):
    t = tenant_id(request)
    out = store.cache_lookup(t, stage_name, stage_schema_version, input_sha256)
    if out is None:
        return {"hit": False}
    return {"hit": True, "output_sha256": out}

@app.post("/cache/record")
def cache_record(request: Request, rec: CacheRecord):
    t = tenant_id(request)
    store.cache_record(t, rec.stage_name, rec.stage_schema_version, rec.input_sha256, rec.output_sha256)
    return {"ok": True}

@app.post("/plan/regenerate")
def plan_regenerate(request: Request, req: RegenerateRequest):
    t = tenant_id(request)
    try:
        return planner.create_plan(t, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/plan/{plan_id}")
def plan_get(request: Request, plan_id: str):
    t = tenant_id(request)
    try:
        return planner.get_plan(t, plan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Plan not found")

@app.get("/plan/{plan_id}/explain")
def plan_explain(request: Request, plan_id: str):
    t = tenant_id(request)
    try:
        return planner.explain_plan(t, plan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Plan not found")

@app.post("/execute/plan")
def plan_execute(request: Request, payload: dict):
    t = tenant_id(request)
    plan_id = payload.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="Missing plan_id")
    planner.mark_executed(t, plan_id)
    return {"ok": True, "plan_id": plan_id, "status": "executed"}


# Dev-only: expose signing public key for diagnostics
@app.get('/dev/signing-public-key')
def dev_signing_public_key(request: Request):
    import os
    if os.getenv('DADI_ENV','dev').strip().lower() not in ('dev','local'):
        raise HTTPException(status_code=404, detail='Not found')
    prov = os.getenv('DADI_SIGNING_PROVIDER','').strip().lower()
    if prov != 'dev_ed25519':
        raise HTTPException(status_code=404, detail='Not found')
    from .dev_ed25519_signing import public_key_jwk
    kid = os.getenv('DADI_SIGNING_KID','dev-k1')
    return {'jwks': {'keys': [public_key_jwk(kid)]}}
