from __future__ import annotations

from typing import Optional, Dict, Any, List
import hashlib

from .db import tx, conn

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def put_artifact(meta, content: bytes) -> Dict[str, Any]:
    h = sha256_hex(content)
    with tx() as c:
        row = c.execute(
            "SELECT sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, storage_ref "
            "FROM artifacts WHERE sha256=%s",
            (h,),
        ).fetchone()
        if row:
            return {
                "sha256": row[0],
                "artifact_type": row[1],
                "schema_version": row[2],
                "media_type": row[3],
                "byte_length": row[4],
                "canonical": row[5],
                "canonical_format": row[6],
                "storage_backend": row[7],
                "storage_ref": row[8],
            }

        c.execute(
            "INSERT INTO artifacts (sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, content) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,'postgres',%s)",
            (h, meta.artifact_type, meta.schema_version, meta.media_type, len(content), meta.canonical, meta.canonical_format, content),
        )

    return {
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

def get_artifact_meta(sha256: str) -> Optional[Dict[str, Any]]:
    with conn() as c:
        row = c.execute(
            "SELECT sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, storage_ref "
            "FROM artifacts WHERE sha256=%s",
            (sha256,),
        ).fetchone()
        if not row:
            return None
        return {
            "sha256": row[0],
            "artifact_type": row[1],
            "schema_version": row[2],
            "media_type": row[3],
            "byte_length": row[4],
            "canonical": row[5],
            "canonical_format": row[6],
            "storage_backend": row[7],
            "storage_ref": row[8],
        }

def get_artifact_content(sha256: str) -> Optional[bytes]:
    with conn() as c:
        row = c.execute("SELECT content, storage_backend FROM artifacts WHERE sha256=%s", (sha256,)).fetchone()
        if not row:
            return None
        content, backend = row
        if backend != "postgres":
            return None
        return content

def record_edge(from_sha256: str, to_sha256: str, edge_type: str, stage_run_id: Optional[str]) -> None:
    with tx() as c:
        c.execute(
            "INSERT INTO artifact_edges (from_sha256, to_sha256, edge_type, stage_run_id) VALUES (%s,%s,%s,%s)",
            (from_sha256, to_sha256, edge_type, stage_run_id),
        )

def lineage_upstream(sha256: str) -> List[Dict[str, Any]]:
    with conn() as c:
        rows = c.execute(
            "SELECT from_sha256, to_sha256, edge_type, stage_run_id, created_at "
            "FROM artifact_edges WHERE to_sha256=%s ORDER BY edge_id ASC",
            (sha256,),
        ).fetchall()
    return [{"from_sha256":r[0],"to_sha256":r[1],"edge_type":r[2],"stage_run_id":r[3],"created_at":r[4].isoformat()} for r in rows]

def lineage_downstream(sha256: str) -> List[Dict[str, Any]]:
    with conn() as c:
        rows = c.execute(
            "SELECT from_sha256, to_sha256, edge_type, stage_run_id, created_at "
            "FROM artifact_edges WHERE from_sha256=%s ORDER BY edge_id ASC",
            (sha256,),
        ).fetchall()
    return [{"from_sha256":r[0],"to_sha256":r[1],"edge_type":r[2],"stage_run_id":r[3],"created_at":r[4].isoformat()} for r in rows]

def cache_lookup(stage_name: str, stage_schema_version: str, input_sha256: str) -> Optional[str]:
    with conn() as c:
        row = c.execute(
            "SELECT output_artifact_sha256 FROM stage_cache WHERE stage_name=%s AND stage_schema_version=%s AND input_artifact_sha256=%s",
            (stage_name, stage_schema_version, input_sha256),
        ).fetchone()
        return row[0] if row else None

def cache_record(stage_name: str, stage_schema_version: str, input_sha256: str, output_sha256: str) -> None:
    with tx() as c:
        c.execute(
            "INSERT INTO stage_cache (stage_name, stage_schema_version, input_artifact_sha256, output_artifact_sha256) "
            "VALUES (%s,%s,%s,%s) ON CONFLICT (stage_name, stage_schema_version, input_artifact_sha256) DO NOTHING",
            (stage_name, stage_schema_version, input_sha256, output_sha256),
        )
