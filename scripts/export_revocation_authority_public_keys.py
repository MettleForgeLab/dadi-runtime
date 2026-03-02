#!/usr/bin/env python3
import os, json, base64
from pathlib import Path

def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def b64url_uint(val: int) -> str:
    raw = val.to_bytes((val.bit_length()+7)//8, "big")
    return b64url(raw)

def main():
    root = Path(__file__).resolve().parents[1]
    out = root / "REVOCATION_AUTHORITY_PUBLIC_KEYS.json"
    provider = os.getenv("REVOCATION_SIGNING_PROVIDER", "aws_kms").strip().lower()
    kid = os.getenv("REVOCATION_SIGNING_KID", "").strip() or "revocation-authority"
    if provider != "aws_kms":
        print("FAIL: only aws_kms supported")
        return 2

    import boto3
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, ec

    region = os.getenv("AWS_REGION","").strip() or os.getenv("AWS_DEFAULT_REGION","").strip() or "us-east-1"
    key_id = os.getenv("AWS_KMS_REVOCATION_KEY_ID","").strip()
    if not key_id:
        print("FAIL: AWS_KMS_REVOCATION_KEY_ID required")
        return 2

    kms = boto3.client("kms", region_name=region)
    pub_der = kms.get_public_key(KeyId=key_id)["PublicKey"]
    pub = serialization.load_der_public_key(pub_der)

    keys = []
    if isinstance(pub, rsa.RSAPublicKey):
        n = pub.public_numbers().n
        e = pub.public_numbers().e
        keys.append({"kid": kid, "kty":"RSA", "n": b64url_uint(n), "e": b64url_uint(e), "alg":"RS256", "use":"sig"})
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        nums = pub.public_numbers()
        keys.append({"kid": kid, "kty":"EC", "crv":"P-256", "x": b64url_uint(nums.x), "y": b64url_uint(nums.y), "alg":"ES256", "use":"sig"})
    else:
        print("FAIL: unsupported key type")
        return 2

    out.write_text(json.dumps({"schema_version":"revocation_authority_keys-v1","keys": keys}, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print("Wrote", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
