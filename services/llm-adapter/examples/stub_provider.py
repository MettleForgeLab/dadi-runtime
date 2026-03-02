from __future__ import annotations

from dadi_llm_adapter.models import LLMRequestV1

class StubProvider:
    def complete(self, request: LLMRequestV1) -> str:
        # Deterministic stub: echoes stable content based on request hashes.
        # Replace with real provider client in production.
        return f"stub_response:model={request.model}:prompt={request.prompt_bundle_sha256[:8]}:inputs={len(request.input_hashes)}"
