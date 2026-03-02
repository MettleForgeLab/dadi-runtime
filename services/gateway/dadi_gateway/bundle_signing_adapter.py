\
from __future__ import annotations

from typing import Any, Dict

from .signing_provider import load_signing_provider, SignatureEnvelope
from .bundle_utils import canonical_json_bytes  # reuse canonicalization

def sign_manifest_with_provider(unsigned_manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds signature object via signing provider.
    unsigned_manifest must NOT contain "signature".
    """
    if "signature" in unsigned_manifest:
        raise ValueError("unsigned_manifest must not include 'signature'")

    provider = load_signing_provider()
    msg = canonical_json_bytes(unsigned_manifest)
    sig = provider.sign(msg)

    manifest = dict(unsigned_manifest)
    manifest["signature"] = sig.as_dict()
    return manifest

def verify_manifest_with_provider(manifest: Dict[str, Any]) -> bool:
    sig_obj = manifest.get("signature")
    if not isinstance(sig_obj, dict):
        return False
    required = ("alg","kid","sig","key_ref")
    if any(k not in sig_obj for k in required):
        return False

    unsigned = dict(manifest)
    unsigned.pop("signature", None)
    msg = canonical_json_bytes(unsigned)

    sig = SignatureEnvelope(
        alg=str(sig_obj["alg"]),
        kid=str(sig_obj["kid"]),
        sig=str(sig_obj["sig"]),
        key_ref=str(sig_obj["key_ref"]),
    )

    provider = load_signing_provider()
    return provider.verify(msg, sig)
