\
from __future__ import annotations

import uuid
import json
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from .db import conn_with_tenant, tx_with_tenant
from .audit import emit_event
from .idempotency import get_idempotency_key, lookup_response, store_response
from .bundle_utils import canonical_json_bytes
from . import store

router = APIRouter(tags=["deliverables"])

def tenant_id(request: Request) -> str:
    t = getattr(request.state, "tenant_id", None)
    if not t:
        raise HTTPException(status_code=401, detail="Unauthorized: tenant context not established")
    return t

def _extract_docx_sha(tenant: str, stage06_output_sha256: str) -> Optional[str]:
    try:
        b = store.get_artifact_content(tenant, stage06_output_sha256)
        if not b:
            return None
        obj = json.loads(b.decode("utf-8"))
        if obj.get("schema_version") != "render_docx_output-v1":
            return None
        return obj.get("results", {}).get("docx_sha256")
    except Exception:
        return None

@router.post("/deliverables")
def create_deliverable(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    ik = get_idempotency_key(request)
    if ik:
        hit = lookup_response(tenant, ik, request.method, request.url.path)
        if hit:
            _, data = hit
            return data
    """
    Create a deliverable record for a pipeline run.

    Input:
      - pipeline_run_id (required)
      - stage06_output_sha256 (optional; if omitted, will attempt to find latest stage06 output for run)
      - status (optional; default draft)
      - supersedes_deliverable_id (optional)

    Output:
      - deliverable_id
      - resolved docx_sha256 (if stage06 pointer available)
    """
    tenant = tenant_id(request)
    pipeline_run_id = payload.get("pipeline_run_id")
    if not pipeline_run_id:
        raise HTTPException(status_code=400, detail="Missing pipeline_run_id")

    status = payload.get("status") or "draft"
    if status not in ("draft","final","sent","superseded"):
        raise HTTPException(status_code=400, detail="Invalid status")

    stage06_out = payload.get("stage06_output_sha256")
    supersedes = payload.get("supersedes_deliverable_id")

    # Resolve stage06 output if not provided
    if not stage06_out:
        with conn_with_tenant(tenant) as c:
            row = c.execute(
                "SELECT output_artifact_sha256 FROM stage_runs "
                "WHERE tenant_id=%s AND pipeline_run_id=%s AND stage_index=6 AND status='success' "
                "ORDER BY completed_at DESC NULLS LAST LIMIT 1",
                (tenant, pipeline_run_id),
            ).fetchone()
        stage06_out = row[0] if row else None

    docx_sha = _extract_docx_sha(tenant, stage06_out) if stage06_out else None

    deliverable_id = str(uuid.uuid4())
    with tx_with_tenant(tenant) as c:
        # Ensure run exists for tenant
        pr = c.execute(
            "SELECT 1 FROM pipeline_runs WHERE tenant_id=%s AND pipeline_run_id=%s",
            (tenant, pipeline_run_id),
        ).fetchone()
        if not pr:
            raise HTTPException(status_code=404, detail="Run not found")

        c.execute(
            "INSERT INTO deliverables (tenant_id, deliverable_id, pipeline_run_id, stage06_output_sha256, docx_sha256, status, supersedes_deliverable_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (tenant, deliverable_id, pipeline_run_id, stage06_out, docx_sha, status, supersedes),
        )

    return {
        "tenant_id": tenant,
        "deliverable_id": deliverable_id,
        "pipeline_run_id": pipeline_run_id,
        "stage06_output_sha256": stage06_out,
        "docx_sha256": docx_sha,
        "status": status,
        "supersedes_deliverable_id": supersedes,
    }

@router.get("/deliverables/{deliverable_id}")
def get_deliverable(request: Request, deliverable_id: str) -> Dict[str, Any]:
    tenant = tenant_id(request)
    with conn_with_tenant(tenant) as c:
        row = c.execute(
            "SELECT deliverable_id, pipeline_run_id, stage06_output_sha256, docx_sha256, status, created_at, supersedes_deliverable_id "
            "FROM deliverables WHERE tenant_id=%s AND deliverable_id=%s",
            (tenant, deliverable_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return {
        "tenant_id": tenant,
        "deliverable_id": str(row[0]),
        "pipeline_run_id": str(row[1]),
        "stage06_output_sha256": row[2],
        "docx_sha256": row[3],
        "status": row[4],
        "created_at": row[5].isoformat() if row[5] else None,
        "supersedes_deliverable_id": str(row[6]) if row[6] else None,
    }

@router.post("/deliverables/{deliverable_id}/finalize")
def finalize_deliverable(request: Request, deliverable_id: str) -> Dict[str, Any]:
    tenant = tenant_id(request)
    ik = get_idempotency_key(request)
    if ik:
        hit = lookup_response(tenant, ik, request.method, request.url.path)
        if hit:
            _, data = hit
            return data

    # Transition to final (fail-closed if deliverable missing)
    with tx_with_tenant(tenant) as c:
        row = c.execute(
            "UPDATE deliverables SET status='final' WHERE tenant_id=%s AND deliverable_id=%s "
            "RETURNING pipeline_run_id, stage06_output_sha256, docx_sha256, status, created_at, supersedes_deliverable_id",
            (tenant, deliverable_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    pipeline_run_id, stage06_out_sha, docx_sha, status, created_at, supersedes = row

    # Create canonical deliverable record artifact
    record_obj = {
        "schema_version": "deliverable_record-v1",
        "tenant_id": tenant,
        "deliverable_id": deliverable_id,
        "pipeline_run_id": str(pipeline_run_id),
        "status": status,
        "created_at": created_at.isoformat() if created_at else None,
        "supersedes_deliverable_id": str(supersedes) if supersedes else None,
        "artifacts": {
            "stage06_output_sha256": stage06_out_sha,
            "docx_sha256": docx_sha,
        },
    }

    record_bytes = canonical_json_bytes(record_obj)
    rec = store.put_artifact(
        tenant,
        type("Meta", (), {
            "artifact_type": "deliverable/record/v1",
            "schema_version": "deliverable_record-v1",
            "media_type": "application/json",
            "canonical": True,
            "canonical_format": "json_c14n_v1",
        }),
        record_bytes,
    )
    record_sha = rec["sha256"]

    # Persist pointer on deliverable row
    with tx_with_tenant(tenant) as c:
        c.execute(
            "UPDATE deliverables SET deliverable_record_sha256=%s WHERE tenant_id=%s AND deliverable_id=%s",
            (record_sha, tenant, deliverable_id),
        )

    result = {"ok": True, "deliverable_id": deliverable_id, "status": "final", "deliverable_record_sha256": record_sha}

    if ik:
        store_response(tenant, ik, request.method, request.url.path, 200, result)
    emit_event(tenant, 'deliverable_created', pipeline_run_id=pipeline_run_id, deliverable_id=deliverable_id, idempotency_key=ik, detail=result)
    return result

@router.post("/deliverables/{deliverable_id}/mark_sent")
def mark_sent(request: Request, deliverable_id: str) -> Dict[str, Any]:
    tenant = tenant_id(request)
    with tx_with_tenant(tenant) as c:
        row = c.execute(
            "UPDATE deliverables SET status='sent' WHERE tenant_id=%s AND deliverable_id=%s RETURNING deliverable_id",
            (tenant, deliverable_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return {"ok": True, "deliverable_id": deliverable_id, "status": "sent"}

@router.post("/deliverables/{deliverable_id}/supersede")
def supersede(request: Request, deliverable_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new deliverable that supersedes the given deliverable.
    Payload must include pipeline_run_id and may include stage06_output_sha256.
    """
    tenant = tenant_id(request)
    # Mark old as superseded
    with tx_with_tenant(tenant) as c:
        row = c.execute(
            "UPDATE deliverables SET status='superseded' WHERE tenant_id=%s AND deliverable_id=%s RETURNING pipeline_run_id",
            (tenant, deliverable_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    # Create new deliverable pointing back
    payload = dict(payload)
    payload["supersedes_deliverable_id"] = deliverable_id
    return create_deliverable(request, payload)

@router.get("/runs/{pipeline_run_id}/deliverables_list")
def list_deliverables_for_run(request: Request, pipeline_run_id: str) -> Dict[str, Any]:
    tenant = tenant_id(request)
    with conn_with_tenant(tenant) as c:
        rows = c.execute(
            "SELECT deliverable_id, stage06_output_sha256, docx_sha256, status, created_at, supersedes_deliverable_id "
            "FROM deliverables WHERE tenant_id=%s AND pipeline_run_id=%s "
            "ORDER BY created_at DESC",
            (tenant, pipeline_run_id),
        ).fetchall()
    return {
        "tenant_id": tenant,
        "pipeline_run_id": pipeline_run_id,
        "deliverables": [
            {
                "deliverable_id": str(r[0]),
                "stage06_output_sha256": r[1],
                "docx_sha256": r[2],
                "status": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "supersedes_deliverable_id": str(r[5]) if r[5] else None,
            }
            for r in rows
        ],
    }
