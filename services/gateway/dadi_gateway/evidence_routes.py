from __future__ import annotations

import io
import json
import uuid
import zipfile
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from .streaming_utils import stream_bytes

from .db import conn_with_tenant, tx_with_tenant
from . import store
from .bundle_utils import canonical_json_bytes
from .manifest_validator import validate_deliverable_manifest
from .evidence_validator import validate_evidence_manifest
from .bundle_utils import sign_manifest, verify_manifest

try:
    from .bundle_signing_adapter import sign_manifest_with_provider, verify_manifest_with_provider
except Exception:
    sign_manifest_with_provider = None
    verify_manifest_with_provider = None

router = APIRouter(tags=["deliverables"])

EVIDENCE_SCOPE = "deliverable:evidence"
EVIDENCE_DOWNLOAD_SCOPE = "deliverable:evidence_download"

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
    try:
        from .audit import emit_event  # type: ignore
    except Exception:
        return
    try:
        emit_event(tenant, event_type, **kwargs)
    except Exception:
        return

def _sign_manifest(unsigned: Dict[str, Any]) -> Dict[str, Any]:
    import os as _os
    if _os.getenv("DADI_SIGNING_PROVIDER","").strip() and sign_manifest_with_provider:
        return sign_manifest_with_provider(unsigned)
    return sign_manifest(unsigned)

def _verify_manifest(manifest: Dict[str, Any]) -> bool:
    import os as _os
    if _os.getenv("DADI_SIGNING_PROVIDER","").strip() and verify_manifest_with_provider:
        return verify_manifest_with_provider(manifest)
    return verify_manifest(manifest)

@router.post("/deliverables/{deliverable_id}/evidence")
def create_evidence(request: Request, deliverable_id: str):
    tenant = tenant_id(request)
    require_scope(request, EVIDENCE_SCOPE)

    with conn_with_tenant(tenant) as c:
        d = c.execute(
            "SELECT pipeline_run_id, status, deliverable_record_sha256, docx_sha256 "
            "FROM deliverables WHERE tenant_id=%s AND deliverable_id=%s",
            (tenant, deliverable_id),
        ).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        pipeline_run_id, status, deliverable_record_sha, docx_sha = d
        if status != "sent":
            raise HTTPException(status_code=409, detail="Deliverable must be sent to generate evidence")

        b = c.execute(
            "SELECT bundle_id, manifest_artifact_sha256, bundle_artifact_sha256 "
            "FROM deliverable_bundles WHERE tenant_id=%s AND deliverable_id=%s AND status='created' "
            "ORDER BY created_at DESC LIMIT 1",
            (tenant, deliverable_id),
        ).fetchone()
        if not b:
            raise HTTPException(status_code=409, detail="No bundle found for deliverable")
        bundle_id, bundle_manifest_sha, bundle_sha = b

    bbytes = store.get_artifact_content(tenant, bundle_manifest_sha)
    if bbytes is None:
        raise HTTPException(status_code=404, detail="Bundle manifest bytes not available")
    bundle_manifest_obj = json.loads(bbytes.decode("utf-8"))
    errs = validate_deliverable_manifest(bundle_manifest_obj)
    if errs:
        raise HTTPException(status_code=400, detail={"error":"bundle_manifest_schema_invalid","errors":errs})
    if not _verify_manifest(bundle_manifest_obj):
        raise HTTPException(status_code=400, detail="Bundle manifest signature invalid")

    # Audit chain verify for run (best-effort)
    audit_chain = None
    try:
        from .audit import _sha256_hex, _canonical_event_bytes
        with conn_with_tenant(tenant) as c:
            rows = c.execute(
                "SELECT event_id, event_type, pipeline_run_id, deliverable_id, bundle_id, idempotency_key, detail_json, prev_event_hash, event_hash "
                "FROM audit_events WHERE tenant_id=%s AND pipeline_run_id=%s AND event_hash IS NOT NULL "
                "ORDER BY created_at ASC, event_id ASC",
                (tenant, str(pipeline_run_id)),
            ).fetchall()
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
                first_error = {"event_id": str(event_id), "expected_prev": prev, "row_prev": prev_hash, "expected_hash": expected, "row_hash": ev_hash}
                break
            prev = ev_hash
            checked += 1
        audit_chain = {"ok": first_error is None, "checked": checked, "chain_head": prev if checked else None, "first_error": first_error}
    except Exception:
        audit_chain = None

    # Metrics snapshot (best-effort)
    metrics = None
    try:
        with conn_with_tenant(tenant) as c:
            rows = c.execute(
                "SELECT stage_index, stage_name, status, started_at, completed_at FROM stage_runs WHERE tenant_id=%s AND pipeline_run_id=%s ORDER BY stage_index ASC",
                (tenant, str(pipeline_run_id)),
            ).fetchall()
        metrics = [{"stage_index": int(r[0]), "stage_name": r[1], "status": r[2],
                    "duration_ms": int((r[4]-r[3]).total_seconds()*1000) if r[3] and r[4] else None} for r in rows]
    except Exception:
        metrics = None

    rec_bytes = store.get_artifact_content(tenant, deliverable_record_sha) if deliverable_record_sha else None
    if rec_bytes is None:
        raise HTTPException(status_code=409, detail="Deliverable record artifact missing; finalize must create it")

    
# Download receipts excerpt (best-effort): last 50 download events for this deliverable
download_receipts = None
try:
    with conn_with_tenant(tenant) as c:
        rows = c.execute(
            "SELECT created_at, event_type, detail_json FROM audit_events "
            "WHERE tenant_id=%s AND deliverable_id=%s AND event_type IN ('bundle_downloaded','evidence_downloaded') "
            "ORDER BY created_at DESC LIMIT 50",
            (tenant, deliverable_id),
        ).fetchall()
    download_receipts = [
        {"created_at": r[0].isoformat() if r[0] else None, "event_type": r[1], "detail": r[2] if isinstance(r[2], dict) else r[2]}
        for r in rows
    ]
except Exception:
    download_receipts = None

# Revocation status for latest bundle/evidence (best-effort)
bundle_status = None
evidence_status = None
try:
    with conn_with_tenant(tenant) as c:
        row = c.execute(
            "SELECT status, revoked_at FROM deliverable_bundles WHERE tenant_id=%s AND deliverable_id=%s AND bundle_id=%s",
            (tenant, deliverable_id, str(bundle_id)),
        ).fetchone()
    if row:
        bundle_status = {"status": row[0], "revoked_at": row[1].isoformat() if row[1] else None}
except Exception:
    bundle_status = None

unsigned = {
        "schema_version": "deliverable_evidence_manifest-v1",
        "tenant_id": tenant,
        "deliverable_id": deliverable_id,
        "pipeline_run_id": str(pipeline_run_id),
        "bundle_id": str(bundle_id),
        "bundle_manifest_sha256": bundle_manifest_sha,
        "bundle_sha256": bundle_sha,
        "deliverable_record_sha256": deliverable_record_sha,
        "docx_sha256": docx_sha,
        "audit_chain": audit_chain,
        "metrics": metrics,
        "download_receipts": download_receipts,
        "bundle_status": bundle_status,
    }
    
# Evidence schema validation (fail-closed): validate unsigned via probe signature and validate signed result.
unsigned_probe = dict(unsigned)
unsigned_probe["signature"] = {"alg": "probe", "kid": "probe", "sig": "probe"}
ev_errs = validate_evidence_manifest(unsigned_probe)
if ev_errs:
    raise HTTPException(status_code=400, detail={"error": "evidence_schema_validation_failed", "errors": ev_errs})

# Referenced artifact existence checks (metadata)
for sha in [bundle_manifest_sha, bundle_sha, deliverable_record_sha]:
    if sha and not store.get_artifact_meta(tenant, sha):
        raise HTTPException(status_code=409, detail="Evidence references missing artifact metadata")

evidence_manifest = _sign_manifest(unsigned)
    ev_errs2 = validate_evidence_manifest(evidence_manifest)
    if ev_errs2:
        raise HTTPException(status_code=400, detail={"error": "evidence_schema_validation_failed", "errors": ev_errs2})
    evidence_manifest_bytes = canonical_json_bytes(evidence_manifest)

    evidence_manifest_sha = store.put_artifact(
        tenant,
        type("Meta", (), {
            "artifact_type": "deliverable/evidence/manifest-v1",
            "schema_version": "deliverable_evidence_manifest-v1",
            "media_type": "application/json",
            "canonical": True,
            "canonical_format": "json_c14n_v1",
        }),
        evidence_manifest_bytes,
    )["sha256"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("evidence_manifest.json", evidence_manifest_bytes)
        z.writestr("bundle_manifest.json", bbytes)
        z.writestr("deliverable_record.json", rec_bytes)
        if audit_chain is not None:
            z.writestr("audit_chain.json", canonical_json_bytes(audit_chain))
        if metrics is not None:
            z.writestr("metrics.json", canonical_json_bytes(metrics))
    bundle_bytes = buf.getvalue()

    evidence_bundle_sha = store.put_artifact(
        tenant,
        type("Meta", (), {
            "artifact_type": "deliverable/evidence/bundle-zip-v1",
            "schema_version": None,
            "media_type": "application/zip",
            "canonical": False,
            "canonical_format": None,
        }),
        bundle_bytes,
    )["sha256"]

    evidence_id = str(uuid.uuid4())
    with tx_with_tenant(tenant) as c:
        c.execute(
            "INSERT INTO deliverable_evidence (tenant_id, evidence_id, deliverable_id, evidence_manifest_sha256, evidence_bundle_sha256) "
            "VALUES (%s,%s,%s,%s,%s)",
            (tenant, evidence_id, deliverable_id, evidence_manifest_sha, evidence_bundle_sha),
        )

    return {
        "tenant_id": tenant,
        "evidence_id": evidence_id,
        "deliverable_id": deliverable_id,
        "evidence_manifest_sha256": evidence_manifest_sha,
        "evidence_bundle_sha256": evidence_bundle_sha,
    }

@router.get("/deliverables/{deliverable_id}/evidence")
def list_evidence(request: Request, deliverable_id: str):
    tenant = tenant_id(request)
    require_scope(request, EVIDENCE_SCOPE)
    with conn_with_tenant(tenant) as c:
        rows = c.execute(
            "SELECT evidence_id, created_at, evidence_manifest_sha256, evidence_bundle_sha256, status "
            "FROM deliverable_evidence WHERE tenant_id=%s AND deliverable_id=%s ORDER BY created_at DESC",
            (tenant, deliverable_id),
        ).fetchall()
    return {
        "tenant_id": tenant,
        "deliverable_id": deliverable_id,
        "evidence": [
            {"evidence_id": str(r[0]), "created_at": r[1].isoformat() if r[1] else None,
             "evidence_manifest_sha256": r[2], "evidence_bundle_sha256": r[3], "status": r[4]}
            for r in rows
        ],
    }

@router.get("/deliverables/{deliverable_id}/evidence/{evidence_id}/download")
def download_evidence(request: Request, deliverable_id: str, evidence_id: str):
    tenant = tenant_id(request)
    require_scope(request, EVIDENCE_DOWNLOAD_SCOPE)

    # Sent-only gate (compliance)
    with conn_with_tenant(tenant) as c:
        d = c.execute(
            "SELECT status FROM deliverables WHERE tenant_id=%s AND deliverable_id=%s",
            (tenant, deliverable_id),
        ).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        if d[0] != "sent":
            _emit_event_if_available(tenant, "evidence_download_denied", deliverable_id=deliverable_id, detail={"reason":"deliverable_not_sent","status": d[0]})
            raise HTTPException(status_code=409, detail="Deliverable must be sent to download evidence")
    with conn_with_tenant(tenant) as c:
        row = c.execute(
            "SELECT evidence_bundle_sha256, status FROM deliverable_evidence WHERE tenant_id=%s AND deliverable_id=%s AND evidence_id=%s",
            (tenant, deliverable_id, evidence_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")
    sha = row[0]
    estatus = row[1]
    if estatus == 'revoked':
        _emit_event_if_available(tenant, 'evidence_download_denied', deliverable_id=deliverable_id, detail={'reason':'revoked','evidence_id': evidence_id})
        raise HTTPException(status_code=409, detail='Evidence is revoked')
    b = store.get_artifact_content(tenant, sha)
    if b is None:
        raise HTTPException(status_code=404, detail="Evidence bundle bytes not available")
    _emit_event_if_available(tenant, "evidence_downloaded", deliverable_id=deliverable_id, detail={"evidence_id": evidence_id, "evidence_sha256": sha, "subject": getattr(request.state, "subject", None)})
    return stream_bytes(b, content_type="application/zip", filename=f"evidence_{evidence_id}.zip")
