from __future__ import annotations

import json
import uuid
from typing import Optional, Dict, Any, Literal, Tuple

from .models import LLMRequestV1, LLMResponseV1
from .hashing import canonical_json_bytes, sha256_hex
from .artifact_store import put_artifact, get_artifact_bytes
from .provider import ProviderClient
from .db import tx

Mode = Literal["live","replay","drift"]

class LLMAdapter:
    def __init__(self, provider: ProviderClient, provider_name: str) -> None:
        self.provider = provider
        self.provider_name = provider_name

    def run(
        self,
        request: LLMRequestV1,
        mode: Mode = "live",
        *,
        expected_response_sha256: Optional[str] = None,
        replay_response_sha256: Optional[str] = None,
        stage_run_id: Optional[str] = None,
        record_ledger: bool = False,
    ) -> Tuple[str, str, Optional[str]]:
        """Execute (or replay) an LLM call.

        Returns: (request_sha256, response_sha256, drift_sha256_or_none)

        - live: call provider, store request/response artifacts
        - replay: load response artifact and return it (no provider call)
        - drift: call provider, compare against expected_response_sha256, emit drift artifact if different
        """
        # Force provider field for determinism
        req = request.model_copy(update={"provider": self.provider_name})

        # Store request artifact
        req_bytes = canonical_json_bytes(req.model_dump())
        req_sha = put_artifact(
            artifact_type="llm/request-v1",
            media_type="application/json",
            content=req_bytes,
            canonical=True,
            canonical_format="json_c14n_v1",
            schema_version="llm_request-v1",
        )

        drift_sha = None

        if mode == "replay":
            if not replay_response_sha256:
                raise ValueError("replay_response_sha256 is required for replay mode")
            resp_bytes = get_artifact_bytes(replay_response_sha256)
            if resp_bytes is None:
                raise KeyError("Replay response artifact not found or not available")
            resp_obj = json.loads(resp_bytes.decode("utf-8"))
            if resp_obj.get("schema_version") != "llm_response-v1":
                raise ValueError("Replay artifact is not llm_response-v1")
            resp_sha = replay_response_sha256

            if record_ledger:
                self._record_ledger(stage_run_id, req_sha, resp_sha, req.provider, req.model, mode)
            return req_sha, resp_sha, None

        # live or drift: call provider
        body = self.provider.complete(req)
        resp = LLMResponseV1(request_sha256=req_sha, provider=req.provider, model=req.model, body=body)
        resp_bytes = canonical_json_bytes(resp.model_dump())
        resp_sha = put_artifact(
            artifact_type="llm/response-v1",
            media_type="application/json",
            content=resp_bytes,
            canonical=True,
            canonical_format="json_c14n_v1",
            schema_version="llm_response-v1",
        )

        if mode == "drift":
            if not expected_response_sha256:
                raise ValueError("expected_response_sha256 is required for drift mode")
            if resp_sha != expected_response_sha256:
                drift = {
                    "schema_version": "llm_drift-v1",
                    "expected_response_sha256": expected_response_sha256,
                    "observed_response_sha256": resp_sha,
                    "request_sha256": req_sha,
                    "provider": req.provider,
                    "model": req.model
                }
                drift_sha = put_artifact(
                    artifact_type="llm/drift-v1",
                    media_type="application/json",
                    content=canonical_json_bytes(drift),
                    canonical=True,
                    canonical_format="json_c14n_v1",
                    schema_version="llm_drift-v1",
                )

        if record_ledger:
            self._record_ledger(stage_run_id, req_sha, resp_sha, req.provider, req.model, mode)

        return req_sha, resp_sha, drift_sha

    def load_response_body(self, response_sha256: str) -> str:
        b = get_artifact_bytes(response_sha256)
        if b is None:
            raise KeyError("Response artifact not found or not available")
        obj = json.loads(b.decode("utf-8"))
        if obj.get("schema_version") != "llm_response-v1":
            raise ValueError("Artifact is not llm_response-v1")
        return obj["body"]

    @staticmethod
    def _record_ledger(stage_run_id: Optional[str], req_sha: str, resp_sha: str, provider: str, model: str, mode: str) -> None:
        if stage_run_id is None:
            return
        llm_call_id = str(uuid.uuid4())
        with tx() as c:
            c.execute(
                "INSERT INTO llm_calls (llm_call_id, stage_run_id, request_artifact_sha256, response_artifact_sha256, provider, model, mode) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (llm_call_id, stage_run_id, req_sha, resp_sha, provider, model, mode),
            )
