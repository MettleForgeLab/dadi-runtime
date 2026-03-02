#!/usr/bin/env python3
import os
import json
import base64
from pathlib import Path

def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def b64url_uint(val: int) -> str:
    raw = val.to_bytes((val.bit_length() + 7) // 8, "big")
    return b64url(raw)

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    att_path = root / "RELEASE_ATTESTATION.json"
    if not att_path.exists():
        print("FAIL: RELEASE_ATTESTATION.json missing")
        return 2

    att = json.loads(att_path.read_text(encoding="utf-8"))
    sig = att.get("signature") or {}
    kid = sig.get("kid")
    alg = sig.get("alg")
    key_ref = sig.get("key_ref")

    if not kid or not alg:
        print("FAIL: signature missing kid/alg")
        return 2

    keys = []

    if alg in ("dev_ed25519", "EdDSA", "ed25519"):
        x = os.getenv("RELEASE_ED25519_PUBLIC_KEY_B64URL", "").strip()
        if not x:
            print("FAIL: RELEASE_ED25519_PUBLIC_KEY_B64URL not set (needed to publish dev_ed25519 public key)")
            return 2
        keys.append({"kid": kid, "kty": "OKP", "crv": "Ed25519", "x": x, "alg": "EdDSA", "use": "sig"})

    elif isinstance(alg, str) and alg.startswith("aws_kms:"):
        import boto3
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa, ec

        if not key_ref:
            key_ref = os.getenv("AWS_KMS_KEY_ID", "").strip()
        if not key_ref:
            print("FAIL: signature.key_ref missing and AWS_KMS_KEY_ID not set")
            return 2

        region = os.getenv("AWS_REGION", "").strip() or os.getenv("AWS_DEFAULT_REGION", "").strip() or "us-east-1"
        kms = boto3.client("kms", region_name=region)
        pub_der = kms.get_public_key(KeyId=key_ref)["PublicKey"]
        pub = serialization.load_der_public_key(pub_der)

        if isinstance(pub, rsa.RSAPublicKey):
            n = pub.public_numbers().n
            e = pub.public_numbers().e
            keys.append({"kid": kid, "kty": "RSA", "n": b64url_uint(n), "e": b64url_uint(e), "alg": "RS256", "use": "sig"})
        elif isinstance(pub, ec.EllipticCurvePublicKey):
            nums = pub.public_numbers()
            keys.append({"kid": kid, "kty": "EC", "crv": "P-256", "x": b64url_uint(nums.x), "y": b64url_uint(nums.y), "alg": "ES256", "use": "sig"})
        else:
            print("FAIL: unsupported public key type from KMS")
            return 2
    else:
        print(f"FAIL: unsupported signing alg for key export: {alg}")
        return 2

    out = {"keys": keys}
    out_path = root / "RELEASE_PUBLIC_KEYS.json"
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote", out_path)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
