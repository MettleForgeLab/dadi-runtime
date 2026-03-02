from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg

def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url

@contextmanager
def conn() -> Iterator[psycopg.Connection]:
    with psycopg.connect(get_database_url()) as c:
        yield c

def get_artifact_bytes(sha256: str) -> bytes:
    with conn() as c:
        row = c.execute("SELECT content, storage_backend FROM artifacts WHERE sha256=%s", (sha256,)).fetchone()
        if not row:
            raise KeyError(f"Artifact not found: {sha256}")
        content, backend = row
        if backend != "postgres" or content is None:
            raise RuntimeError(f"Artifact content not available in postgres backend: {sha256}")
        return content

def put_artifact_bytes(artifact_type: str, media_type: str, content: bytes, canonical: bool = False,
                       canonical_format: str | None = None, schema_version: str | None = None) -> str:
    import hashlib
    h = hashlib.sha256(content).hexdigest()
    with conn() as c:
        with c.transaction():
            row = c.execute("SELECT sha256 FROM artifacts WHERE sha256=%s", (h,)).fetchone()
            if row:
                return h
            c.execute(
                "INSERT INTO artifacts (sha256, artifact_type, schema_version, media_type, byte_length, canonical, canonical_format, storage_backend, content) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,'postgres',%s)",
                (h, artifact_type, schema_version, media_type, len(content), canonical, canonical_format, content),
            )
    return h
