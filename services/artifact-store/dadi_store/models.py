from __future__ import annotations

from typing import Optional, Literal, Any, Dict, List
from pydantic import BaseModel, Field, constr

Sha256 = constr(pattern=r"^[a-fA-F0-9]{64}$")

class ArtifactCreate(BaseModel):
    artifact_type: str
    media_type: str
    canonical: bool = False
    canonical_format: Optional[str] = None
    schema_version: Optional[str] = None  # for JSON artifacts, mirror payload.schema_version if present

class ArtifactRecord(BaseModel):
    sha256: Sha256
    artifact_type: str
    schema_version: Optional[str] = None
    media_type: str
    byte_length: int
    canonical: bool
    canonical_format: Optional[str] = None
    storage_backend: Literal["postgres","blob"]
    storage_ref: Optional[str] = None

class EdgeCreate(BaseModel):
    from_sha256: Sha256
    to_sha256: Sha256
    edge_type: Literal["consumes","produces","references","base_of_delta"]
    stage_run_id: Optional[str] = None  # UUID string

class CacheLookup(BaseModel):
    stage_name: str
    stage_schema_version: str
    input_sha256: Sha256

class CacheRecord(BaseModel):
    stage_name: str
    stage_schema_version: str
    input_sha256: Sha256
    output_sha256: Sha256
