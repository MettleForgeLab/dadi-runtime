from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


def canonical_json_bytes(obj: Any) -> bytes:
    """
    Canonical-ish JSON for signing:
    - UTF-8
    - stable key ordering
    - stable separators (no whitespace)
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


@dataclass(frozen=True)
class Signature:
    """
    Stored in manifest as:
      { "alg": "...", "kid": "...", "sig": "base64url..." }
    """
    alg: str
    kid: str
    sig: str  # base64url

    def as_dict(self) -> Dict[str, str]:
        return {"alg": self.alg, "kid": self.kid, "sig": self.sig}


def _load_signing_alg() -> str:
    # Prefer Ed25519 for audit-grade bundles.
    # Allow override for bootstrap.
    return os.getenv("DADI_BUNDLE_SIGNING_ALG", "ed25519").lower().strip()


def _load_kid() -> str:
    kid = os.getenv("DADI_BUNDLE_SIGNING_KID", "").strip()
    if not kid:
        raise RuntimeError("DADI_BUNDLE_SIGNING_KID is not set")
    return kid


def _load_hmac_secrets() -> Dict[str, bytes]:
    """
    Rotation support for HMAC:
      DADI_HMAC_SECRETS_JSON='{"kid1":"base64urlsecret","kid2":"base64urlsecret"}'
    """
    raw = os.getenv("DADI_HMAC_SECRETS_JSON", "").strip()
    if not raw:
        # Backward-compatible single secret:
        secret = os.getenv("DADI_BUNDLE_SIGNING_SECRET", "").strip()
        if not secret:
            return {}
        kid = os.getenv("DADI_BUNDLE_SIGNING_KID", "default")
        return {kid: secret.encode("utf-8")}

    data = json.loads(raw)
    out: Dict[str, bytes] = {}
    for kid, b64s in data.items():
        out[str(kid)] = _b64url_decode(str(b64s))
    return out


def _load_ed25519_keys() -> Tuple[Dict[str, bytes], Dict[str, bytes]]:
    """
    Rotation support for Ed25519 (public keys required for verify; private key required for sign):

      DADI_ED25519_PUBLIC_KEYS_JSON='{"kid1":"base64url_pubkey_bytes", ... }'
      DADI_ED25519_PRIVATE_KEYS_JSON='{"kid1":"base64url_privkey_seed_32_bytes", ... }'   (only on signer hosts)

    Key bytes are the raw Ed25519 key bytes:
      - public key: 32 bytes
      - private key: 32 bytes seed (for cryptography)
    """
    pub_raw = os.getenv("DADI_ED25519_PUBLIC_KEYS_JSON", "").strip()
    priv_raw = os.getenv("DADI_ED25519_PRIVATE_KEYS_JSON", "").strip()

    pubs: Dict[str, bytes] = {}
    privs: Dict[str, bytes] = {}

    if pub_raw:
        data = json.loads(pub_raw)
        for kid, b64k in data.items():
            pubs[str(kid)] = _b64url_decode(str(b64k))

    if priv_raw:
        data = json.loads(priv_raw)
        for kid, b64k in data.items():
            privs[str(kid)] = _b64url_decode(str(b64k))

    # Backward-compatible single-key envs (optional):
    pub1 = os.getenv("DADI_ED25519_PUBLIC_KEY_B64URL", "").strip()
    priv1 = os.getenv("DADI_ED25519_PRIVATE_KEY_B64URL", "").strip()
    if pub1:
        kid = os.getenv("DADI_BUNDLE_SIGNING_KID", "default")
        pubs.setdefault(kid, _b64url_decode(pub1))
    if priv1:
        kid = os.getenv("DADI_BUNDLE_SIGNING_KID", "default")
        privs.setdefault(kid, _b64url_decode(priv1))

    return pubs, privs


def sign_manifest(unsigned_manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a new manifest dict with a structured signature field:
      manifest["signature"] = {alg, kid, sig}

    unsigned_manifest must NOT contain "signature".
    """
    if "signature" in unsigned_manifest:
        raise ValueError("unsigned_manifest must not include 'signature'")

    alg = _load_signing_alg()
    kid = _load_kid()
    unsigned_bytes = canonical_json_bytes(unsigned_manifest)

    if alg == "hmac-sha256":
        secrets = _load_hmac_secrets()
        key = secrets.get(kid)
        if not key:
            raise RuntimeError("No HMAC key found for kid (check DADI_HMAC_SECRETS_JSON / DADI_BUNDLE_SIGNING_SECRET)")
        sig = hmac.new(key, unsigned_bytes, hashlib.sha256).digest()
        signature = Signature(alg="hmac-sha256", kid=kid, sig=_b64url_encode(sig))

    elif alg == "ed25519":
        pubs, privs = _load_ed25519_keys()
        priv = privs.get(kid)
        if not priv:
            raise RuntimeError("No Ed25519 private key found for kid (check DADI_ED25519_PRIVATE_KEYS_JSON / DADI_ED25519_PRIVATE_KEY_B64URL)")

        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except Exception as e:
            raise RuntimeError("Ed25519 signing requires 'cryptography' package") from e

        if len(priv) != 32:
            raise RuntimeError("Ed25519 private key must be 32-byte seed (base64url-decoded) for cryptography")

        sk = Ed25519PrivateKey.from_private_bytes(priv)
        sig = sk.sign(unsigned_bytes)
        signature = Signature(alg="ed25519", kid=kid, sig=_b64url_encode(sig))

    else:
        raise RuntimeError(f"Unsupported signing alg: {alg}")

    manifest = dict(unsigned_manifest)
    manifest["signature"] = signature.as_dict()
    return manifest


def verify_manifest(manifest: Dict[str, Any]) -> bool:
    """
    Verify manifest["signature"] against the canonical bytes of manifest without signature.
    """
    sig_obj = manifest.get("signature")
    if not isinstance(sig_obj, dict):
        return False

    alg = sig_obj.get("alg")
    kid = sig_obj.get("kid")
    sig_b64 = sig_obj.get("sig")
    if not (isinstance(alg, str) and isinstance(kid, str) and isinstance(sig_b64, str)):
        return False

    unsigned = dict(manifest)
    unsigned.pop("signature", None)
    unsigned_bytes = canonical_json_bytes(unsigned)

    try:
        sig = _b64url_decode(sig_b64)
    except Exception:
        return False

    if alg == "hmac-sha256":
        secrets = _load_hmac_secrets()
        key = secrets.get(kid)
        if not key:
            return False
        expected = hmac.new(key, unsigned_bytes, hashlib.sha256).digest()
        return hmac.compare_digest(expected, sig)

    if alg == "ed25519":
        pubs, _ = _load_ed25519_keys()
        pub = pubs.get(kid)
        if not pub:
            return False
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        except Exception:
            return False
        if len(pub) != 32:
            return False
        pk = Ed25519PublicKey.from_public_bytes(pub)
        try:
            pk.verify(sig, unsigned_bytes)
            return True
        except Exception:
            return False

    return False
