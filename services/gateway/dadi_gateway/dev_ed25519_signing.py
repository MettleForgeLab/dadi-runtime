\
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Dict

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .signing_provider import SignatureEnvelope, SigningProvider

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

# Singleton keypair per process
_sk = Ed25519PrivateKey.generate()
_pk = _sk.public_key()

@dataclass
class DevEd25519SigningProvider(SigningProvider):
    kid: str

    @classmethod
    def from_env(cls) -> "DevEd25519SigningProvider":
        kid = os.getenv("DADI_SIGNING_KID", "").strip() or "dev-k1"
        return cls(kid=kid)

    def healthcheck(self) -> None:
        # Always available in-process
        return

    def sign(self, message: bytes) -> SignatureEnvelope:
        sig = _sk.sign(message)
        return SignatureEnvelope(
            alg="dev_ed25519",
            kid=self.kid,
            sig=_b64url(sig),
            key_ref="in-memory",
        )

    def verify(self, message: bytes, signature: SignatureEnvelope) -> bool:
        try:
            sig_bytes = _b64url_decode(signature.sig)
            _pk.verify(sig_bytes, message)
            return True
        except Exception:
            return False

def public_key_b64url() -> str:
    pub = _pk.public_bytes_raw()
    return _b64url(pub)

def public_key_jwk(kid: str) -> Dict[str, str]:
    # Minimal JWK-like object
    return {"kty": "OKP", "crv": "Ed25519", "kid": kid, "x": public_key_b64url(), "use": "sig", "alg": "EdDSA"}
