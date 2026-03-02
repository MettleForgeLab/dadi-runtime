from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .db import conn_with_tenant, tx_with_tenant

router = APIRouter(tags=["deliverables"])

def tenant_id(request: Request) -> str:
    t = getattr(request.state, "tenant_id", None)
    if not t:
        raise HTTPException(status_code=401, detail="Unauthorized: tenant context not established")
    return t

def _emit_event_if_available(tenant: str, event_type: str, **kwargs):
    try:
        from .audit import emit_event  # type: ignore
    except Exception:
        return
    try:
        emit_event(tenant, event_type, **kwargs)
    except Exception:
        return

@router.post("/deliverables/{deliverable_id}/bundles/{bundle_id}/revoke")
def revoke_bundle(request: Request, deliverable_id: str, bundle_id: str):
    tenant = tenant_id(request)
    with tx_with_tenant(tenant) as c:
        row = c.execute(
            "UPDATE deliverable_bundles SET status='revoked', revoked_at=now() "
            "WHERE tenant_id=%s AND deliverable_id=%s AND bundle_id=%s AND status!='revoked' "
            "RETURNING bundle_id",
            (tenant, deliverable_id, bundle_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Bundle not found or already revoked")
    _emit_event_if_available(tenant, "bundle_revoked", deliverable_id=deliverable_id, bundle_id=bundle_id, detail={})
    return {"ok": True, "bundle_id": bundle_id, "status": "revoked"}

@router.post("/deliverables/{deliverable_id}/evidence/{evidence_id}/revoke")
def revoke_evidence(request: Request, deliverable_id: str, evidence_id: str):
    tenant = tenant_id(request)
    with tx_with_tenant(tenant) as c:
        row = c.execute(
            "UPDATE deliverable_evidence SET status='revoked', revoked_at=now() "
            "WHERE tenant_id=%s AND deliverable_id=%s AND evidence_id=%s AND status!='revoked' "
            "RETURNING evidence_id",
            (tenant, deliverable_id, evidence_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found or already revoked")
    _emit_event_if_available(tenant, "evidence_revoked", deliverable_id=deliverable_id, detail={"evidence_id": evidence_id})
    return {"ok": True, "evidence_id": evidence_id, "status": "revoked"}
