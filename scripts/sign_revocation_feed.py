#!/usr/bin/env python3
import json, os, base64, hashlib
from datetime import datetime, timezone
from pathlib import Path
def b64url(raw: bytes)->str: return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
def canonical_bytes(obj: dict)->bytes: return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def main():
    root=Path(__file__).resolve().parents[1]
    feedp=root/"REVOCATION_FEED.json"
    if not feedp.exists(): print("FAIL: REVOCATION_FEED.json missing"); return 2
    obj=json.loads(feedp.read_text(encoding="utf-8"))
    unsigned=dict(obj); unsigned["signature"]=None
    msg=canonical_bytes(unsigned)
    payload_sha=hashlib.sha256(msg).hexdigest()
    provider=os.getenv("REVOCATION_SIGNING_PROVIDER","aws_kms").strip().lower()
    kid=os.getenv("REVOCATION_SIGNING_KID","revocation-authority").strip()
    if provider!="aws_kms": print("FAIL: only aws_kms supported"); return 2
    import boto3
    region=os.getenv("AWS_REGION","").strip() or "us-east-1"
    key_id=os.getenv("AWS_KMS_REVOCATION_KEY_ID","").strip()
    alg=os.getenv("AWS_KMS_SIGNING_ALG","ECDSA_SHA_256").strip()
    if not key_id: print("FAIL: AWS_KMS_REVOCATION_KEY_ID required"); return 2
    kms=boto3.client("kms",region_name=region)
    resp=kms.sign(KeyId=key_id,Message=msg,MessageType="RAW",SigningAlgorithm=alg)
    obj["signature"]={"alg":f"aws_kms:{alg}","kid":kid,"sig":b64url(resp["Signature"]),"key_ref":key_id}
    obj["payload_sha256"]=payload_sha
    obj["signed_at_utc"]=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    feedp.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("Signed REVOCATION_FEED.json"); return 0
if __name__=="__main__": raise SystemExit(main())
