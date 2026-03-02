#!/usr/bin/env python3
import json, base64, hashlib
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding as asy_padding
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import hashes
def b64url_decode(s:str)->bytes:
    pad="="*(-len(s)%4); return base64.urlsafe_b64decode(s+pad)
def jwk_to_public_key(jwk:dict):
    kty=jwk.get("kty")
    if kty=="OKP" and jwk.get("crv")=="Ed25519": return Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))
    if kty=="RSA":
        n=int.from_bytes(b64url_decode(jwk["n"]),"big"); e=int.from_bytes(b64url_decode(jwk["e"]),"big")
        return rsa.RSAPublicNumbers(e,n).public_key()
    if kty=="EC":
        if jwk.get("crv")!="P-256": raise ValueError("Unsupported EC crv")
        x=int.from_bytes(b64url_decode(jwk["x"]),"big"); y=int.from_bytes(b64url_decode(jwk["y"]),"big")
        return ec.EllipticCurvePublicNumbers(x,y,ec.SECP256R1()).public_key()
    raise ValueError("Unsupported JWK")
def canonical_bytes(obj:dict)->bytes:
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def verify_sig(msg:bytes,sig:dict,auth:dict)->bool:
    keys=auth.get("keys") or []
    kid=sig.get("kid"); alg=sig.get("alg"); sb=sig.get("sig")
    if not kid or not alg or not sb: return False
    jwk=next((k for k in keys if k.get("kid")==kid),None)
    if not jwk: return False
    pub=jwk_to_public_key(jwk); sig_raw=b64url_decode(sb)
    try:
        if isinstance(alg,str) and alg.startswith("aws_kms:"):
            if isinstance(pub,rsa.RSAPublicKey): pub.verify(sig_raw,msg,asy_padding.PKCS1v15(),hashes.SHA256()); return True
            if isinstance(pub,ec.EllipticCurvePublicKey): pub.verify(sig_raw,msg,ec.ECDSA(hashes.SHA256())); return True
        return False
    except Exception: return False
def main():
    root=Path(__file__).resolve().parents[1]
    fp=root/"REVOCATION_FEED.json"
    if not fp.exists(): print("FAIL: REVOCATION_FEED.json missing"); return 2
    obj=json.loads(fp.read_text(encoding="utf-8"))
    sig=obj.get("signature"); auth=obj.get("revocation_authority_public_keys")
    if not isinstance(sig,dict) or not isinstance(auth,dict): print("FAIL: missing signature/authority"); return 2
    unsigned=dict(obj); unsigned["signature"]=None
    unsigned.pop("payload_sha256",None); unsigned.pop("signed_at_utc",None)
    msg=canonical_bytes(unsigned)
    expected=hashlib.sha256(msg).hexdigest()
    if obj.get("payload_sha256") and obj.get("payload_sha256")!=expected: print("FAIL: payload_sha256 mismatch"); return 2
    ok=verify_sig(msg,sig,auth); print("OK" if ok else "FAIL"); return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
