#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    asset_path = Path(args.asset).resolve()
    if not asset_path.exists():
        print("FAIL: asset not found")
        return 2

    digest = sha256_file(asset_path)
    provider = os.getenv("DADI_SIGNING_PROVIDER","").strip().lower()
    kid = os.getenv("DADI_SIGNING_KID","").strip() or "unknown"
    sig_obj = None

    if provider == "aws_kms":
        import boto3
        region = os.getenv("AWS_REGION","").strip() or "us-east-1"
        key_id = os.getenv("AWS_KMS_KEY_ID","").strip()
        alg = os.getenv("AWS_KMS_SIGNING_ALG","ECDSA_SHA_256").strip()
        if not key_id:
            print("FAIL: AWS_KMS_KEY_ID required")
            return 2
        kms = boto3.client("kms", region_name=region)
        msg = digest.encode("ascii")
        resp = kms.sign(KeyId=key_id, Message=msg, MessageType="RAW", SigningAlgorithm=alg)
        sig = resp["Signature"]
        sig_obj = {"alg": f"aws_kms:{alg}", "kid": kid, "sig": b64url(sig), "key_ref": key_id}

    elif provider == "dev_ed25519":
        seed_b64 = os.getenv("RELEASE_ED25519_PRIVATE_SEED_B64URL","").strip()
        if not seed_b64:
            print("FAIL: RELEASE_ED25519_PRIVATE_SEED_B64URL required for dev attestation")
            return 2
        pad = "=" * (-len(seed_b64) % 4)
        seed = base64.urlsafe_b64decode(seed_b64 + pad)
        if len(seed) != 32:
            print("FAIL: dev seed must be 32 bytes")
            return 2
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        sk = Ed25519PrivateKey.from_private_bytes(seed)
        sig = sk.sign(digest.encode("ascii"))
        sig_obj = {"alg": "dev_ed25519", "kid": kid, "sig": b64url(sig)}
    else:
        print("FAIL: DADI_SIGNING_PROVIDER must be aws_kms or dev_ed25519")
        return 2

    att = {
        "schema_version": "asset_attestation-v1",
        "asset": asset_path.name,
        "sha256": digest,
        "signature": sig_obj,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }

    Path(args.out).write_text(json.dumps(att, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print("Wrote", args.out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
