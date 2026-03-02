\
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, Dict, Any, Optional

@dataclass(frozen=True)
class SignatureEnvelope:
    alg: str
    kid: str
    sig: str      # base64url
    key_ref: str  # provider key reference (e.g., KMS KeyId/ARN)

    def as_dict(self) -> Dict[str, str]:
        return {"alg": self.alg, "kid": self.kid, "sig": self.sig, "key_ref": self.key_ref}

class SigningProvider(Protocol):
    def sign(self, message: bytes) -> SignatureEnvelope:
        ...

    def verify(self, message: bytes, signature: SignatureEnvelope) -> bool:
        ...

    def healthcheck(self) -> None:
        """Raise on misconfiguration/unavailability."""
        ...

def load_signing_provider() -> SigningProvider:
    provider = os.getenv("DADI_SIGNING_PROVIDER", "").strip().lower()
    if provider == "dev_ed25519":
        from .dev_ed25519_signing import DevEd25519SigningProvider
        return DevEd25519SigningProvider.from_env()
    if provider == "aws_kms":
        from .aws_kms_signing import AWSKMSSigningProvider
        return AWSKMSSigningProvider.from_env()
    raise RuntimeError("DADI_SIGNING_PROVIDER must be set to a supported provider (e.g., aws_kms)")
