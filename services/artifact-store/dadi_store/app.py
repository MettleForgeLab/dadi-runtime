from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import Optional

from .models import ArtifactCreate, EdgeCreate, CacheRecord
from .store import (
    put_artifact_bytes, get_artifact_meta, get_artifact_content,
    record_edge, lineage_upstream, lineage_downstream,
    cache_lookup, cache_record
)

app = FastAPI(title="DADI Artifact Store", version="0.1.0")

@app.post("/artifacts")
async def create_artifact(meta: ArtifactCreate, content_b64: str):
    """
    Store artifact bytes.

    content_b64: base64-encoded bytes.
    In production you'd stream bytes; this is minimal.
    """
    import base64
    try:
        content = base64.b64decode(content_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 content")

    rec = put_artifact_bytes(meta, content)
    return rec.model_dump()

@app.get("/artifacts/{sha256}")
async def artifact_meta(sha256: str):
    rec = get_artifact_meta(sha256)
    if not rec:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return rec.model_dump()

@app.get("/artifacts/{sha256}/content")
async def artifact_content(sha256: str):
    content = get_artifact_content(sha256)
    if content is None:
        raise HTTPException(status_code=404, detail="Artifact content not available (missing or non-postgres backend)")
    return Response(content=content, media_type="application/octet-stream")

@app.post("/edges")
async def create_edge(edge: EdgeCreate):
    record_edge(edge.from_sha256, edge.to_sha256, edge.edge_type, edge.stage_run_id)
    return {"ok": True}

@app.get("/lineage/{sha256}/upstream")
async def get_upstream(sha256: str):
    return {"edges": lineage_upstream(sha256)}

@app.get("/lineage/{sha256}/downstream")
async def get_downstream(sha256: str):
    return {"edges": lineage_downstream(sha256)}

@app.get("/cache/lookup")
async def get_cache(stage_name: str, stage_schema_version: str, input_sha256: str):
    out = cache_lookup(stage_name, stage_schema_version, input_sha256)
    if out is None:
        return {"hit": False}
    return {"hit": True, "output_sha256": out}

@app.post("/cache/record")
async def post_cache(rec: CacheRecord):
    cache_record(rec.stage_name, rec.stage_schema_version, rec.input_sha256, rec.output_sha256)
    return {"ok": True}
