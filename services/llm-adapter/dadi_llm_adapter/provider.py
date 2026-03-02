from __future__ import annotations

from typing import Protocol

from .models import LLMRequestV1

class ProviderClient(Protocol):
    def complete(self, request: LLMRequestV1) -> str:
        """Return provider response body as text."""
        ...
