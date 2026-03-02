from __future__ import annotations

import os
from typing import Iterable, Iterator, Optional

def iter_bytes(data: bytes, chunk_size: int) -> Iterator[bytes]:
    for i in range(0, len(data), chunk_size):
        yield data[i:i+chunk_size]

def stream_bytes(data: bytes, *, content_type: str, filename: Optional[str] = None, content_length: Optional[int] = None):
    """Return a StreamingResponse-compatible iterable and headers.

    Note: data is already in memory in the Postgres-byte backend. This avoids additional copies and enables chunked send.
    For a true large-object/blob backend, replace with a DB/blob streaming iterator.
    """
    from starlette.responses import StreamingResponse

    chunk_size = int(os.getenv("DADI_STREAM_CHUNK_SIZE", str(256 * 1024)))  # 256KB
    max_bytes = os.getenv("DADI_MAX_STREAM_BYTES", "").strip()
    if max_bytes:
        mb = int(max_bytes)
        if len(data) > mb:
            # fail-closed
            from fastapi import HTTPException
            raise HTTPException(status_code=413, detail="Stream exceeds configured maximum")

    headers = {}
    if filename:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    if content_length is None:
        content_length = len(data)
    headers["Content-Length"] = str(content_length)

    return StreamingResponse(iter_bytes(data, chunk_size), media_type=content_type, headers=headers)
