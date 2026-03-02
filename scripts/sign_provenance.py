#!/usr/bin/env python3
import json, hashlib, os, base64
from pathlib import Path
from datetime import datetime, timezone

def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def b64url_decode(s: str) -> bytes:
    pad="=" * (-len(s)%4)
    return base64.urlsafe_b64decode(s+pad)

def main():
    root=Path(__file__).resolve().parents[1]
    p=root/"PROVENANCE.json"
    if not p.exists():
        print("FAIL: PROVENANCE.json missing"); return 2
    msg=p.read_bytes()
    msha=hashlib.sha256(msg).hexdigest()
    provider=os.getenv("DADI_SIGNING_PROVIDER","").strip().lower()
    kid=os.getenv("DADI_SIGNING_KID","").strip() or "unknown"
    sig_obj=None
    if provider=="dev_ed25519":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        seed_b64=os.getenv("RELEASE_ED25519_PRIVATE_SEED_B64URL","").strip()
        if not seed_b64:
            print("FAIL: RELEASE_ED25519_PRIVATE_SEED_B64URL required"); return 2
        seed=b64url_decode(seed_b64)
        if len(seed)!=32:
            print("FAIL: seed must be 32 bytes"); return 2
        sk=Ed25519PrivateKey.from_private_bytes(seed)
        sig=sk.sign(msg)
        sig_obj={"alg":"dev_ed25519","kid":kid,"sig":b64url(sig)}
    elif provider=="aws_kms":
        import boto3
        region=os.getenv("AWS_REGION","").strip() or "us-east-1"
        key_id=os.getenv("AWS_KMS_KEY_ID","").strip()
        alg=os.getenv("AWS_KMS_SIGNING_ALG","ECDSA_SHA_256").strip()
        if not key_id:
            print("FAIL: AWS_KMS_KEY_ID required"); return 2
        kms=boto3.client("kms", region_name=region)
        resp=kms.sign(KeyId=key_id, Message=msg, MessageType="RAW", SigningAlgorithm=alg)
        sig=resp["Signature"]
        sig_obj={"alg":f"aws_kms:{alg}","kid":kid,"sig":b64url(sig),"key_ref":key_id}
    else:
        print("FAIL: DADI_SIGNING_PROVIDER must be dev_ed25519 or aws_kms"); return 2
    att={"schema_version":"provenance_attestation-v1","provenance_sha256":msha,"signature":sig_obj,"created_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    (root/"PROVENANCE_ATTESTATION.json").write_text(json.dumps(att,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("Wrote PROVENANCE_ATTESTATION.json"); return 0

if __name__=="__main__":
    raise SystemExit(main())
