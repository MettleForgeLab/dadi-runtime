from __future__ import annotations

from typing import Optional

from .db import tx, conn, get_tenant_id
from .hashing import sha256_hex

def put_artifact(artifact_type: str, media_type: str, content: bytes, canonical: bool,
                 canonical_format: Optional[str] = None, schema_version: Optional[str] = None) -> str:
    tenant_id = get_tenant_id()
    h = sha256_hex(content)
    with tx() as c:
        row = c.execute("SELECT sha256 FROM artifacts WHERE tenant_id=%s AND sha256=%s", (tenant_id, h)).fetchone()
        if row:
            return h
        c.execute(
            "INSERT INTO artifacts (tenant_id, sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, content) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'postgres',%s)",
            (tenant_id, h, artifact_type, schema_version, media_type, len(content), canonical, canonical_format, content),
        )
    return h

def get_artifact_content(sha256: str) -> Optional[bytes]:
    tenant_id = get_tenant_id()
    with conn() as c:
        row = c.execute("SELECT content, storage_backend FROM artifacts WHERE tenant_id=%s AND sha256=%s", (tenant_id, sha256)).fetchone()
        if not row:
            return None
        content, backend = row
        if backend != "postgres":
            return None
        return content

def record_edge(from_sha256: str, to_sha256: str, edge_type: str, stage_run_id: Optional[str] = None) -> None:
    tenant_id = get_tenant_id()
    with tx() as c:
        c.execute(
            "INSERT INTO artifact_edges (tenant_id, from_sha256, to_sha256, edge_type, stage_run_id) VALUES (%s,%s,%s,%s,%s)",
            (tenant_id, from_sha256, to_sha256, edge_type, stage_run_id),
        )

def cache_lookup(stage_name: str, stage_schema_version: str, input_sha256: str) -> Optional[str]:
    tenant_id = get_tenant_id()
    with conn() as c:
        row = c.execute(
            "SELECT output_artifact_sha256 FROM stage_cache WHERE tenant_id=%s AND stage_name=%s AND stage_schema_version=%s AND input_artifact_sha256=%s",
            (tenant_id, stage_name, stage_schema_version, input_sha256),
        ).fetchone()
        return row[0] if row else None

def cache_record(stage_name: str, stage_schema_version: str, input_sha256: str, output_sha256: str) -> None:
    tenant_id = get_tenant_id()
    with tx() as c:
        c.execute(
            "INSERT INTO stage_cache (tenant_id, stage_name, stage_schema_version, input_artifact_sha256, output_artifact_sha256) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, stage_name, stage_schema_version, input_artifact_sha256) DO NOTHING",
            (tenant_id, stage_name, stage_schema_version, input_sha256, output_sha256),
        )

def insert_stage_run(pipeline_run_id: str, stage_index: int, stage_name: str, stage_schema_version: str,
                     toolchain_manifest_sha256: str, prompt_bundle_sha256: Optional[str],
                     input_artifact_sha256: str) -> str:
    import uuid
    tenant_id = get_tenant_id()
    stage_run_id = str(uuid.uuid4())
    with tx() as c:
        c.execute(
            "INSERT INTO stage_runs (tenant_id, stage_run_id, pipeline_run_id, stage_index, stage_name, stage_schema_version, "
            "toolchain_manifest_sha256, prompt_bundle_sha256, input_artifact_sha256, status, fail_closed) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'failed',false)",
            (tenant_id, stage_run_id, pipeline_run_id, stage_index, stage_name, stage_schema_version, toolchain_manifest_sha256,
             prompt_bundle_sha256, input_artifact_sha256),
        )
    return stage_run_id

def finalize_stage_run_success(stage_run_id: str, output_artifact_sha256: str) -> None:
    tenant_id = get_tenant_id()
    with tx() as c:
        c.execute(
            "UPDATE stage_runs SET status='success', output_artifact_sha256=%s, completed_at=now() WHERE tenant_id=%s AND stage_run_id=%s",
            (output_artifact_sha256, tenant_id, stage_run_id),
        )

def finalize_stage_run_fail_closed(stage_run_id: str, error_artifact_sha256: str) -> None:
    tenant_id = get_tenant_id()
    with tx() as c:
        c.execute(
            "UPDATE stage_runs SET status='failed', fail_closed=true, deterministic_error_artifact_sha256=%s, completed_at=now() "
            "WHERE tenant_id=%s AND stage_run_id=%s",
            (error_artifact_sha256, tenant_id, stage_run_id),
        )
