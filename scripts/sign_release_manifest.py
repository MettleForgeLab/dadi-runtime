#!/usr/bin/env python3
import json, os, base64, hashlib
from pathlib import Path

def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")

def main():
    root = Path(__file__).resolve().parents[1]
    mpath = root / "RELEASE_MANIFEST.json"
    if not mpath.exists():
        raise SystemExit("RELEASE_MANIFEST.json missing")
    mbytes = mpath.read_bytes()
    msha = hashlib.sha256(mbytes).hexdigest()

    # If a signing provider is available in this repo environment, use it.
    # Otherwise sign with an explicit Ed25519 private key from env (base64url 32-byte seed).
    provider = os.getenv("DADI_SIGNING_PROVIDER","").strip().lower()
    kid = os.getenv("DADI_SIGNING_KID","release-dev-k1").strip() or "release-dev-k1"

    if provider:
        try:
            from services.gateway.dadi_gateway.bundle_utils import canonical_json_bytes
            from services.gateway.dadi_gateway.signing_provider import load_signing_provider
            from services.gateway.dadi_gateway.signing_provider import SignatureEnvelope
            p = load_signing_provider()
            sig = p.sign(mbytes)
            att = {
                "schema_version":"release_attestation-v1",
                "manifest_sha256": msha,
                "signature": sig.as_dict(),
            }
            (root/"RELEASE_ATTESTATION.json").write_text(json.dumps(att, indent=2, sort_keys=True)+"\n", encoding="utf-8")
            print("Wrote RELEASE_ATTESTATION.json using provider:", provider)
            return 0
        except Exception as e:
            print("Provider signing failed, falling back to env key:", str(e))

    seed_b64 = os.getenv("RELEASE_ED25519_SEED_B64URL","").strip()
    if not seed_b64:
        raise SystemExit("Set RELEASE_ED25519_SEED_B64URL (base64url 32-byte seed) or configure DADI_SIGNING_PROVIDER")

    pad = "=" * (-len(seed_b64) % 4)
    seed = base64.urlsafe_b64decode(seed_b64 + pad)
    if len(seed) != 32:
        raise SystemExit("RELEASE_ED25519_SEED_B64URL must decode to 32 bytes")

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sk = Ed25519PrivateKey.from_private_bytes(seed)
    pk = sk.public_key()
    sig = sk.sign(mbytes)

    att = {
        "schema_version":"release_attestation-v1",
        "manifest_sha256": msha,
        "signature": {
            "alg":"ed25519",
            "kid": kid,
            "sig": b64url(sig),
            "public_key_b64url": b64url(pk.public_bytes_raw()),
        }
    }
    (root/"RELEASE_ATTESTATION.json").write_text(json.dumps(att, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print("Wrote RELEASE_ATTESTATION.json using env seed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
