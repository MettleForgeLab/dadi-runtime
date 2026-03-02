\
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Optional

import boto3
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from .signing_provider import SignatureEnvelope, SigningProvider
from .kms_public_key_cache import KMS_PUBKEY_CACHE

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

@dataclass
class AWSKMSSigningProvider(SigningProvider):
    region: str
    key_id: str
    kid: str
    signing_alg: str

    _client: any

    @classmethod
    def from_env(cls) -> "AWSKMSSigningProvider":
        region = os.getenv("AWS_REGION", "").strip()
        key_id = os.getenv("AWS_KMS_KEY_ID", "").strip()
        kid = os.getenv("DADI_SIGNING_KID", "").strip()
        signing_alg = os.getenv("AWS_KMS_SIGNING_ALG", "ECDSA_SHA_256").strip()

        if not region:
            raise RuntimeError("AWS_REGION is required")
        if not key_id:
            raise RuntimeError("AWS_KMS_KEY_ID is required")
        if not kid:
            raise RuntimeError("DADI_SIGNING_KID is required")

        client = boto3.client("kms", region_name=region)
        return cls(region=region, key_id=key_id, kid=kid, signing_alg=signing_alg, _client=client)

    def healthcheck(self) -> None:
        # Validate we can fetch public key and sign (dry run)
        self._client.get_public_key(KeyId=self.key_id)

    def sign(self, message: bytes) -> SignatureEnvelope:
        resp = self._client.sign(
            KeyId=self.key_id,
            Message=message,
            MessageType="RAW",
            SigningAlgorithm=self.signing_alg,
        )
        sig_bytes = resp["Signature"]
        alg = f"aws_kms:{self.signing_alg}"
        return SignatureEnvelope(alg=alg, kid=self.kid, sig=_b64url_encode(sig_bytes), key_ref=self.key_id)

    def verify(self, message: bytes, signature: SignatureEnvelope) -> bool:
        # Verify locally using public key fetched from KMS.
        # KMS ECDSA signatures are DER-encoded; cryptography can verify DER directly.
        sig_bytes = _b64url_decode(signature.sig)

        alg = signature.alg
        pub = KMS_PUBKEY_CACHE.get(signature.kid, signature.key_ref, alg)
        if pub is None:
            try:
                pub = self._client.get_public_key(KeyId=signature.key_ref)["PublicKey"]
                KMS_PUBKEY_CACHE.put(signature.kid, signature.key_ref, alg, pub)
            except Exception:
                return False
        pubkey = serialization.load_der_public_key(pub)

        # Map algorithm to hash/padding
        # Only handle common SHA256 variants here.
        if "SHA_256" in signature.alg:
            h = hashes.SHA256()
        elif "SHA_384" in signature.alg:
            h = hashes.SHA384()
        elif "SHA_512" in signature.alg:
            h = hashes.SHA512()
        else:
            return False

        try:
            if isinstance(pubkey, ec.EllipticCurvePublicKey):
                pubkey.verify(sig_bytes, message, ec.ECDSA(h))
                return True
            if isinstance(pubkey, rsa.RSAPublicKey):
                if "PSS" in signature.alg:
                    pubkey.verify(sig_bytes, message, padding.PSS(mgf=padding.MGF1(h), salt_length=padding.PSS.MAX_LENGTH), h)
                    return True
                # default PKCS1v15
                pubkey.verify(sig_bytes, message, padding.PKCS1v15(), h)
                return True
        except Exception:
            return False
        return False
