from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from .streaming_utils import stream_bytes

from .db import conn_with_tenant
from . import store

router = APIRouter(tags=["deliverables"])

DOWNLOAD_SCOPE = "deliverable:download_bundle"

def tenant_id(request: Request) -> str:
    t = getattr(request.state, "tenant_id", None)
    if not t:
        raise HTTPException(status_code=401, detail="Unauthorized: tenant context not established")
    return t

def require_scope(request: Request, required: str) -> None:
    scopes = getattr(request.state, "scopes", set()) or set()
    if required not in scopes:
        raise HTTPException(status_code=403, detail="Forbidden: insufficient scope")

def _emit_event_if_available(tenant: str, event_type: str, **kwargs):
    # Optional integration: if audit.emit_event exists in gateway, call it.
    try:
        from .audit import emit_event  # type: ignore
    except Exception:
        return
    try:
        emit_event(tenant, event_type, **kwargs)
    except Exception:
        return

@router.get("/deliverables/{deliverable_id}/bundles/{bundle_id}/download")
def download_bundle(request: Request, deliverable_id: str, bundle_id: str):
    tenant = tenant_id(request)
    require_scope(request, DOWNLOAD_SCOPE)

    with conn_with_tenant(tenant) as c:
        d = c.execute(
            "SELECT status FROM deliverables WHERE tenant_id=%s AND deliverable_id=%s",
            (tenant, deliverable_id),
        ).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        status = d[0]
        if status != "sent":
            _emit_event_if_available(tenant, "bundle_download_denied", deliverable_id=deliverable_id, bundle_id=bundle_id, detail={"reason": "deliverable_not_sent", "status": status})
            raise HTTPException(status_code=409, detail="Deliverable must be sent to download bundle")

        row = c.execute(
            "SELECT bundle_artifact_sha256, status FROM deliverable_bundles WHERE tenant_id=%s AND bundle_id=%s AND deliverable_id=%s",
            (tenant, bundle_id, deliverable_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bundle not found")

    bundle_sha = row[0]
    bstatus = row[1]
    if bstatus == 'revoked':
        _emit_event_if_available(tenant, 'bundle_download_denied', deliverable_id=deliverable_id, bundle_id=bundle_id, detail={'reason':'revoked'})
        raise HTTPException(status_code=409, detail='Bundle is revoked')
    b = store.get_artifact_content(tenant, bundle_sha)
    if b is None:
        raise HTTPException(status_code=404, detail="Bundle bytes not available")

    _emit_event_if_available(tenant, "bundle_downloaded", deliverable_id=deliverable_id, bundle_id=bundle_id, detail={"bundle_sha256": bundle_sha, "subject": getattr(request.state, "subject", None)})

    return stream_bytes(b, content_type="application/zip", filename=f"bundle_{bundle_id}.zip")
