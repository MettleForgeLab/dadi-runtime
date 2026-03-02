from __future__ import annotations

from typing import Optional

from .db import tx, conn
from .hashing import sha256_hex

def put_artifact(artifact_type: str, media_type: str, content: bytes, canonical: bool,
                 canonical_format: str | None = None, schema_version: str | None = None) -> str:
    h = sha256_hex(content)
    with tx() as c:
        row = c.execute("SELECT sha256 FROM artifacts WHERE sha256=%s", (h,)).fetchone()
        if row:
            return h
        c.execute(
            "INSERT INTO artifacts (sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, content) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,'postgres',%s)",
            (h, artifact_type, schema_version, media_type, len(content), canonical, canonical_format, content),
        )
    return h

def get_artifact_bytes(sha256: str) -> Optional[bytes]:
    with conn() as c:
        row = c.execute("SELECT content, storage_backend FROM artifacts WHERE sha256=%s", (sha256,)).fetchone()
        if not row:
            return None
        content, backend = row
        if backend != "postgres":
            return None
        return content
