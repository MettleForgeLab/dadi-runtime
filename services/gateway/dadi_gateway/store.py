from __future__ import annotations

from typing import Optional, Dict, Any, List
import hashlib

from .db import tx_with_tenant, conn_with_tenant

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def put_artifact(tenant_id: str, meta, content: bytes) -> Dict[str, Any]:
    h = sha256_hex(content)
    with tx_with_tenant(tenant_id) as c:
        row = c.execute(
            "SELECT tenant_id, sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, storage_ref "
            "FROM artifacts WHERE tenant_id=%s AND sha256=%s",
            (tenant_id, h),
        ).fetchone()
        if row:
            return {
                "tenant_id": row[0],
                "sha256": row[1],
                "artifact_type": row[2],
                "schema_version": row[3],
                "media_type": row[4],
                "byte_length": row[5],
                "canonical": row[6],
                "canonical_format": row[7],
                "storage_backend": row[8],
                "storage_ref": row[9],
            }

        c.execute(
            "INSERT INTO artifacts (tenant_id, sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, content) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'postgres',%s)",
            (tenant_id, h, meta.artifact_type, meta.schema_version, meta.media_type, len(content), meta.canonical, meta.canonical_format, content),
        )

    return {
        "tenant_id": tenant_id,
        "sha256": h,
        "artifact_type": meta.artifact_type,
        "schema_version": meta.schema_version,
        "media_type": meta.media_type,
        "byte_length": len(content),
        "canonical": meta.canonical,
        "canonical_format": meta.canonical_format,
        "storage_backend": "postgres",
        "storage_ref": None,
    }

def get_artifact_meta(tenant_id: str, sha256: str) -> Optional[Dict[str, Any]]:
    with conn_with_tenant(tenant_id) as c:
        row = c.execute(
            "SELECT tenant_id, sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, storage_ref "
            "FROM artifacts WHERE tenant_id=%s AND sha256=%s",
            (tenant_id, sha256),
        ).fetchone()
        if not row:
            return None
        return {
            "tenant_id": row[0],
            "sha256": row[1],
            "artifact_type": row[2],
            "schema_version": row[3],
            "media_type": row[4],
            "byte_length": row[5],
            "canonical": row[6],
            "canonical_format": row[7],
            "storage_backend": row[8],
            "storage_ref": row[9],
        }

def get_artifact_content(tenant_id: str, sha256: str) -> Optional[bytes]:
    with conn_with_tenant(tenant_id) as c:
        row = c.execute("SELECT content, storage_backend FROM artifacts WHERE tenant_id=%s AND sha256=%s", (tenant_id, sha256)).fetchone()
        if not row:
            return None
        content, backend = row
        if backend != "postgres":
            return None
        return content

def record_edge(tenant_id: str, from_sha256: str, to_sha256: str, edge_type: str, stage_run_id: Optional[str]) -> None:
    with tx_with_tenant(tenant_id) as c:
        c.execute(
            "INSERT INTO artifact_edges (tenant_id, from_sha256, to_sha256, edge_type, stage_run_id) VALUES (%s,%s,%s,%s,%s)",
            (tenant_id, from_sha256, to_sha256, edge_type, stage_run_id),
        )

def lineage_upstream(tenant_id: str, sha256: str) -> List[Dict[str, Any]]:
    with conn_with_tenant(tenant_id) as c:
        rows = c.execute(
            "SELECT from_sha256, to_sha256, edge_type, stage_run_id, created_at "
            "FROM artifact_edges WHERE tenant_id=%s AND to_sha256=%s ORDER BY edge_id ASC",
            (tenant_id, sha256),
        ).fetchall()
    return [{"from_sha256":r[0],"to_sha256":r[1],"edge_type":r[2],"stage_run_id":r[3],"created_at":r[4].isoformat()} for r in rows]

def lineage_downstream(tenant_id: str, sha256: str) -> List[Dict[str, Any]]:
    with conn_with_tenant(tenant_id) as c:
        rows = c.execute(
            "SELECT from_sha256, to_sha256, edge_type, stage_run_id, created_at "
            "FROM artifact_edges WHERE tenant_id=%s AND from_sha256=%s ORDER BY edge_id ASC",
            (tenant_id, sha256),
        ).fetchall()
    return [{"from_sha256":r[0],"to_sha256":r[1],"edge_type":r[2],"stage_run_id":r[3],"created_at":r[4].isoformat()} for r in rows]

def cache_lookup(tenant_id: str, stage_name: str, stage_schema_version: str, input_sha256: str) -> Optional[str]:
    with conn_with_tenant(tenant_id) as c:
        row = c.execute(
            "SELECT output_artifact_sha256 FROM stage_cache WHERE tenant_id=%s AND stage_name=%s AND stage_schema_version=%s AND input_artifact_sha256=%s",
            (tenant_id, stage_name, stage_schema_version, input_sha256),
        ).fetchone()
        return row[0] if row else None

def cache_record(tenant_id: str, stage_name: str, stage_schema_version: str, input_sha256: str, output_sha256: str) -> None:
    with tx_with_tenant(tenant_id) as c:
        c.execute(
            "INSERT INTO stage_cache (tenant_id, stage_name, stage_schema_version, input_artifact_sha256, output_artifact_sha256) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (tenant_id, stage_name, stage_schema_version, input_artifact_sha256) DO NOTHING",
            (tenant_id, stage_name, stage_schema_version, input_sha256, output_sha256),
        )
