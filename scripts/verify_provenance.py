#!/usr/bin/env python3
import json, hashlib, base64
from pathlib import Path

def b64url_decode(s: str) -> bytes:
    pad="=" * (-len(s)%4)
    return base64.urlsafe_b64decode(s+pad)

def main():
    root=Path(__file__).resolve().parents[1]
    p=root/"PROVENANCE.json"; a=root/"PROVENANCE_ATTESTATION.json"
    if not p.exists() or not a.exists():
        print("FAIL: missing provenance or attestation"); return 2
    msg=p.read_bytes()
    msha=hashlib.sha256(msg).hexdigest()
    att=json.loads(a.read_text(encoding="utf-8"))
    if att.get("provenance_sha256")!=msha:
        print("FAIL: provenance_sha256 mismatch"); return 2
    sig=att.get("signature") or {}
    kid=sig.get("kid"); alg=sig.get("alg"); sig_b64=sig.get("sig")
    if not kid or not alg or not sig_b64:
        print("FAIL: missing signature fields"); return 2
    sig_raw=b64url_decode(sig_b64)
    pk=root/"RELEASE_PUBLIC_KEYS.json"
    if not pk.exists():
        print("SKIP: RELEASE_PUBLIC_KEYS.json missing"); return 0
    jwks=json.loads(pk.read_text(encoding="utf-8"))
    jwk=next((k for k in (jwks.get("keys") or []) if k.get("kid")==kid), None)
    if not jwk:
        print("FAIL: public key not found"); return 2
    kty=jwk.get("kty")
    try:
        if kty=="OKP" and jwk.get("crv")=="Ed25519":
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pub=Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))
            pub.verify(sig_raw, msg); print("OK"); return 0
        if kty=="RSA":
            from cryptography.hazmat.primitives.asymmetric import rsa, padding
            from cryptography.hazmat.primitives import hashes
            n=int.from_bytes(b64url_decode(jwk["n"]),"big")
            e=int.from_bytes(b64url_decode(jwk["e"]),"big")
            pub=rsa.RSAPublicNumbers(e,n).public_key()
            pub.verify(sig_raw, msg, padding.PKCS1v15(), hashes.SHA256()); print("OK"); return 0
        if kty=="EC":
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import hashes
            x=int.from_bytes(b64url_decode(jwk["x"]),"big")
            y=int.from_bytes(b64url_decode(jwk["y"]),"big")
            pub=ec.EllipticCurvePublicNumbers(x,y,ec.SECP256R1()).public_key()
            pub.verify(sig_raw, msg, ec.ECDSA(hashes.SHA256())); print("OK"); return 0
    except Exception as e:
        print("FAIL:", str(e)); return 2
    print("FAIL: unsupported key type"); return 2

if __name__=="__main__":
    raise SystemExit(main())
