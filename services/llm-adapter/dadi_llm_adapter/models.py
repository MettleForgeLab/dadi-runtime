from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, constr

Sha256 = constr(pattern=r"^[a-fA-F0-9]{64}$")

class LLMRequestV1(BaseModel):
    schema_version: Literal["llm_request-v1"] = "llm_request-v1"
    provider: str
    model: str
    prompt_bundle_sha256: Sha256
    toolchain_manifest_sha256: Sha256
    input_hashes: List[Sha256] = Field(default_factory=list)
    decoding: Dict[str, Any] = Field(default_factory=dict)
    tools: Dict[str, Any] = Field(default_factory=dict)  # may include function schema hashes, tool routing, etc.

class LLMResponseV1(BaseModel):
    schema_version: Literal["llm_response-v1"] = "llm_response-v1"
    request_sha256: Sha256
    provider: str
    model: str
    body: str  # store raw text; if you prefer bytes, base64 encode upstream.
