from __future__ import annotations

import io
import json
import uuid
import zipfile
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Request

from .db import conn_with_tenant, tx_with_tenant
from .audit import emit_event
from .idempotency import get_idempotency_key, lookup_response, store_response
from . import store
from .bundle_utils import canonical_json_bytes, sign_manifest, verify_manifest
from .bundle_signing_adapter import sign_manifest_with_provider, verify_manifest_with_provider
from .manifest_validator import validate_deliverable_manifest
from .closure_verify import expected_stage_runs_v1_artifacts, expected_stage_runs_v1_sources, verify_closure_stage_runs_v1

router = APIRouter(tags=["deliverables"])

def tenant_id(request: Request) -> str:
    t = getattr(request.state, "tenant_id", None)
    if not t:
        raise HTTPException(status_code=401, detail="Unauthorized: tenant context not established")
    return t

def _collect_run_artifacts(tenant: str, pipeline_run_id: str) -> List[str]:
    with conn_with_tenant(tenant) as c:
        rows = c.execute(
            "SELECT toolchain_manifest_sha256, prompt_bundle_sha256, input_artifact_sha256, output_artifact_sha256, deterministic_error_artifact_sha256 "
            "FROM stage_runs WHERE tenant_id=%s AND pipeline_run_id=%s",
            (tenant, pipeline_run_id),
        ).fetchall()
    s: Set[str] = set()
    for tool_sha, prompt_sha, in_sha, out_sha, err_sha in rows:
        if tool_sha: s.add(tool_sha)
        if prompt_sha: s.add(prompt_sha)
        if in_sha: s.add(in_sha)
        if out_sha: s.add(out_sha)
        if err_sha: s.add(err_sha)
    return sorted(s)

def _artifact_meta_or_404(tenant: str, sha: str) -> Dict[str, Any]:
    m = store.get_artifact_meta(tenant, sha)
    if not m:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {sha}")
    return m

def _artifact_bytes_or_404(tenant: str, sha: str) -> bytes:
    b = store.get_artifact_content(tenant, sha)
    if b is None:
        raise HTTPException(status_code=404, detail=f"Artifact bytes not available: {sha}")
    return b

@router.post("/deliverables/{deliverable_id}/bundle")
def create_bundle(request: Request, deliverable_id: str) -> Dict[str, Any]:
    tenant = tenant_id(request)
    ik = get_idempotency_key(request)
    if ik:
        hit = lookup_response(tenant, ik, request.method, request.url.path)
        if hit:
            _, data = hit
            return data

    with conn_with_tenant(tenant) as c:
        d = c.execute(
            "SELECT pipeline_run_id, stage06_output_sha256, docx_sha256, status, deliverable_record_sha256 "
            "FROM deliverables WHERE tenant_id=%s AND deliverable_id=%s",
            (tenant, deliverable_id),
        ).fetchone()
    if not d:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    pipeline_run_id, stage06_out_sha, docx_sha, status, deliverable_record_sha = d



    # Fail closed: deliverable must resolve docx bytes before bundling
    if not docx_sha:
        raise HTTPException(status_code=409, detail=\"Deliverable has no docx_sha256; render Stage 06 before bundling\")
    # Policy gate: bundle creation requires finalized deliverable
    if status not in (\"final\", \"sent\"):
        raise HTTPException(status_code=409, detail=\"Deliverable must be final or sent to create a bundle\")
    artifacts = set(_collect_run_artifacts(tenant, str(pipeline_run_id)))
    if stage06_out_sha:
        artifacts.add(stage06_out_sha)
    if docx_sha:
        artifacts.add(docx_sha)
    if deliverable_record_sha:
        artifacts.add(deliverable_record_sha)

    artifact_entries: List[Dict[str, Any]] = []
    artifact_bytes_map: Dict[str, bytes] = {}

    for sha in sorted(artifacts):
        meta = _artifact_meta_or_404(tenant, sha)
        b = _artifact_bytes_or_404(tenant, sha)
        artifact_bytes_map[sha] = b
        artifact_entries.append({
            "sha256": sha,
            "artifact_type": meta.get("artifact_type"),
            "schema_version": meta.get("schema_version"),
            "media_type": meta.get("media_type"),
            "byte_length": meta.get("byte_length"),
        })

    unsigned = {
        "schema_version": "deliverable_manifest-v1",
        "closure_mode": "stage_runs_v1",
        "tenant_id": tenant,
        "deliverable_id": deliverable_id,
        "pipeline_run_id": str(pipeline_run_id),
        "deliverable_status": status,
        "stage06_output_sha256": stage06_out_sha,
        "docx_sha256": docx_sha,
        "artifacts": artifact_entries,
    }

    # Schema validation (fail-closed) before and after signing
# Validate unsigned shape using a stub signature, then validate signed manifest.
unsigned_probe = dict(unsigned)
unsigned_probe["signature"] = {"alg": "probe", "kid": "probe", "sig": "probe"}
errs = validate_deliverable_manifest(unsigned_probe)
if errs:
    raise HTTPException(status_code=400, detail={"error": "manifest_schema_validation_failed", "errors": errs})
import os as _os
    if _os.getenv('DADI_SIGNING_PROVIDER','').strip():
        manifest = sign_manifest_with_provider(unsigned)
    else:
        manifest = sign_manifest(unsigned)
    errs2 = validate_deliverable_manifest(manifest)
    if errs2:
        raise HTTPException(status_code=400, detail={"error": "manifest_schema_validation_failed", "errors": errs2})
    manifest_bytes = canonical_json_bytes(manifest)
    signature = manifest["signature"]
manifest_sha = store.put_artifact(
        tenant,
        type("Meta", (), {
            "artifact_type": "deliverable/manifest/v1",
            "schema_version": "deliverable_manifest-v1",
        "closure_mode": "stage_runs_v1",
            "media_type": "application/json",
            "canonical": True,
            "canonical_format": "json_c14n_v1",
        }),
        manifest_bytes,
    )["sha256"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", manifest_bytes)
        for sha in sorted(artifact_bytes_map.keys()):
            z.writestr(f"artifacts/{sha}", artifact_bytes_map[sha])
    bundle_bytes = buf.getvalue()

    bundle_sha = store.put_artifact(
        tenant,
        type("Meta", (), {
            "artifact_type": "deliverable/bundle/zip-v1",
            "schema_version": None,
            "media_type": "application/zip",
            "canonical": False,
            "canonical_format": None,
        }),
        bundle_bytes,
    )["sha256"]

    bundle_id = str(uuid.uuid4())
    with tx_with_tenant(tenant) as c:
        c.execute(
            "INSERT INTO deliverable_bundles (tenant_id, deliverable_id, bundle_id, manifest_artifact_sha256, bundle_artifact_sha256) "
            "VALUES (%s,%s,%s,%s,%s)",
            (tenant, deliverable_id, bundle_id, manifest_sha, bundle_sha),
        )

    return {
        "tenant_id": tenant,
        "deliverable_id": deliverable_id,
        "bundle_id": bundle_id,
        "manifest_artifact_sha256": manifest_sha,
        "bundle_artifact_sha256": bundle_sha,
        "signature": signature,
    }

@router.get("/deliverables/{deliverable_id}/bundles")
def list_bundles(request: Request, deliverable_id: str) -> Dict[str, Any]:
    tenant = tenant_id(request)
    with conn_with_tenant(tenant) as c:
        rows = c.execute(
            "SELECT bundle_id, created_at, manifest_artifact_sha256, bundle_artifact_sha256, status "
            "FROM deliverable_bundles WHERE tenant_id=%s AND deliverable_id=%s ORDER BY created_at DESC",
            (tenant, deliverable_id),
        ).fetchall()
    return {
        "tenant_id": tenant,
        "deliverable_id": deliverable_id,
        "bundles": [
            {
                "bundle_id": str(r[0]),
                "created_at": r[1].isoformat() if r[1] else None,
                "manifest_artifact_sha256": r[2],
                "bundle_artifact_sha256": r[3],
                "status": r[4],
            }
            for r in rows
        ],
    }

@router.post("/deliverables/{deliverable_id}/bundle/verify")
def verify_bundle(request: Request, deliverable_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify a manifest signature and basic semantic correctness.

    Input: { "manifest_artifact_sha256": "<sha>" }

    Checks:
    - manifest exists and is JSON
    - schema_version == deliverable_manifest-v1
    - tenant_id matches request tenant
    - signature verifies against unsigned canonical bytes
    - listed artifacts exist in DB for this tenant (metadata existence)
    """
    tenant = tenant_id(request)
    msha = payload.get("manifest_artifact_sha256")
    if not msha:
        raise HTTPException(status_code=400, detail="Missing manifest_artifact_sha256")

    b = store.get_artifact_content(tenant, msha)
    if b is None:
        raise HTTPException(status_code=404, detail="Manifest artifact not found")

    try:
        manifest = json.loads(b.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Manifest artifact is not valid JSON")

    if manifest.get("schema_version") != "deliverable_manifest-v1":
        raise HTTPException(status_code=400, detail="Manifest schema_version is not deliverable_manifest-v1")

    if manifest.get("tenant_id") != tenant:
        raise HTTPException(status_code=403, detail="Manifest tenant_id does not match request tenant")

    errs = validate_deliverable_manifest(manifest)
    if errs:
        raise HTTPException(status_code=400, detail={"error": "manifest_schema_validation_failed", "errors": errs})

    import os as _os
    if _os.getenv('DADI_SIGNING_PROVIDER','').strip():
        ok = verify_manifest_with_provider(manifest)
    else:
        ok = verify_manifest(manifest)
    if not ok:
        return {"ok": False, "manifest_artifact_sha256": msha}

    missing = []
    for a in manifest.get("artifacts", []) or []:
        sha = a.get("sha256") if isinstance(a, dict) else None
        if not isinstance(sha, str) or len(sha) != 64:
            continue
        if not store.get_artifact_meta(tenant, sha):
            missing.append(sha)

    run_id = manifest.get("pipeline_run_id")
    expected = expected_stage_runs_v1_artifacts(tenant, run_id)
    sources = expected_stage_runs_v1_sources(tenant, run_id)
    closure_mode = manifest.get("closure_mode")
    closure = None
    if closure_mode == "stage_runs_v1":
        closure = verify_closure_stage_runs_v1(manifest, expected)
        # Add diagnostic context for missing artifacts
        if closure and closure.get("missing_expected_artifacts"):
            closure["missing_expected_details"] = [
                {"sha256": sha, "sources": sources.get(sha, [])}
                for sha in closure.get("missing_expected_artifacts")
            ]
    result = {"ok": True, "manifest_artifact_sha256": msha, "missing_artifacts": missing, "closure": closure}