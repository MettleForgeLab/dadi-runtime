from __future__ import annotations

import json
import uuid
import hashlib
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, Request

from .db import conn_with_tenant, tx_with_tenant

router = APIRouter(tags=["audit"])

def tenant_id(request: Request) -> str:
    t = getattr(request.state, "tenant_id", None)
    if not t:
        raise HTTPException(status_code=401, detail="Unauthorized: tenant context not established")
    return t

def _canonical_event_bytes(event: Dict[str, Any]) -> bytes:
    return json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def emit_event(
    tenant: str,
    event_type: str,
    *,
    pipeline_run_id: Optional[str] = None,
    deliverable_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    detail: Dict[str, Any] | None = None,
) -> str:
    detail = detail or {}
    event_id = str(uuid.uuid4())

    with tx_with_tenant(tenant) as c:
        row = c.execute(
            "SELECT event_hash FROM audit_events WHERE tenant_id=%s AND event_hash IS NOT NULL "
            "ORDER BY created_at DESC, event_id DESC LIMIT 1",
            (tenant,),
        ).fetchone()
        prev_hash = row[0] if row and row[0] else None

        event_for_hash = {
            "tenant_id": tenant,
            "event_id": event_id,
            "event_type": event_type,
            "pipeline_run_id": pipeline_run_id,
            "deliverable_id": deliverable_id,
            "bundle_id": bundle_id,
            "idempotency_key": idempotency_key,
            "detail": detail,
        }
        msg = (prev_hash or "0"*64).encode("ascii") + b"|" + _canonical_event_bytes(event_for_hash)
        event_hash = _sha256_hex(msg)

        c.execute(
            "INSERT INTO audit_events (tenant_id, event_id, event_type, pipeline_run_id, deliverable_id, bundle_id, idempotency_key, detail_json, prev_event_hash, event_hash) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)",
            (tenant, event_id, event_type, pipeline_run_id, deliverable_id, bundle_id, idempotency_key, json.dumps(detail), prev_hash, event_hash),
        )

    return event_id

@router.get("/audit")
def get_audit(
    request: Request,
    pipeline_run_id: Optional[str] = None,
    deliverable_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    tenant = tenant_id(request)
    limit = max(1, min(int(limit), 500))

    where = ["tenant_id=%s"]
    params: List[Any] = [tenant]
    if pipeline_run_id:
        where.append("pipeline_run_id=%s")
        params.append(pipeline_run_id)
    if deliverable_id:
        where.append("deliverable_id=%s")
        params.append(deliverable_id)
    if bundle_id:
        where.append("bundle_id=%s")
        params.append(bundle_id)

    q = (
        "SELECT event_id, created_at, event_type, pipeline_run_id, deliverable_id, bundle_id, idempotency_key, detail_json, prev_event_hash, event_hash "
        "FROM audit_events WHERE " + " AND ".join(where) + " ORDER BY created_at DESC LIMIT %s"
    )
    params.append(limit)

    with conn_with_tenant(tenant) as c:
        rows = c.execute(q, params).fetchall()

    events = []
    for r in rows:
        events.append({
            "event_id": str(r[0]),
            "created_at": r[1].isoformat() if r[1] else None,
            "event_type": r[2],
            "pipeline_run_id": str(r[3]) if r[3] else None,
            "deliverable_id": str(r[4]) if r[4] else None,
            "bundle_id": str(r[5]) if r[5] else None,
            "idempotency_key": r[6],
            "detail": r[7] if isinstance(r[7], dict) else r[7],
            "prev_event_hash": r[8],
            "event_hash": r[9],
        })

    return {"tenant_id": tenant, "events": events}

@router.get("/audit/verify-chain")
def verify_chain(
    request: Request,
    pipeline_run_id: Optional[str] = None,
    deliverable_id: Optional[str] = None,
    limit: int = 500
) -> Dict[str, Any]:
    tenant = tenant_id(request)
    limit = max(1, min(int(limit), 5000))

    where = ["tenant_id=%s", "event_hash IS NOT NULL"]
    params: List[Any] = [tenant]
    if pipeline_run_id:
        where.append("pipeline_run_id=%s")
        params.append(pipeline_run_id)
    if deliverable_id:
        where.append("deliverable_id=%s")
        params.append(deliverable_id)

    q = (
        "SELECT event_id, event_type, pipeline_run_id, deliverable_id, bundle_id, idempotency_key, detail_json, prev_event_hash, event_hash "
        "FROM audit_events WHERE " + " AND ".join(where) + " ORDER BY created_at ASC, event_id ASC LIMIT %s"
    )
    params.append(limit)

    with conn_with_tenant(tenant) as c:
        rows = c.execute(q, params).fetchall()

    prev = "0"*64
    first_error = None
    checked = 0
    for r in rows:
        event_id, event_type, pr, did, bid, ik, detail_json, prev_hash, ev_hash = r
        event_for_hash = {
            "tenant_id": tenant,
            "event_id": str(event_id),
            "event_type": event_type,
            "pipeline_run_id": str(pr) if pr else None,
            "deliverable_id": str(did) if did else None,
            "bundle_id": str(bid) if bid else None,
            "idempotency_key": ik,
            "detail": detail_json if isinstance(detail_json, dict) else detail_json,
        }
        msg = prev.encode("ascii") + b"|" + _canonical_event_bytes(event_for_hash)
        expected = _sha256_hex(msg)

        if (prev_hash or "0"*64) != prev or ev_hash != expected:
            first_error = {
                "event_id": str(event_id),
                "expected_prev": prev,
                "row_prev": prev_hash,
                "expected_hash": expected,
                "row_hash": ev_hash,
            }
            break

        prev = ev_hash
        checked += 1

    return {"tenant_id": tenant, "ok": first_error is None, "checked": checked, "first_error": first_error}
