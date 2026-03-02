#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding as asy_padding
from cryptography.hazmat.primitives import hashes

def b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def jwk_to_public_key(jwk: dict):
    kty = jwk.get("kty")
    if kty == "OKP" and jwk.get("crv") == "Ed25519":
        return Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))
    if kty == "RSA":
        n = int.from_bytes(b64url_decode(jwk["n"]), "big")
        e = int.from_bytes(b64url_decode(jwk["e"]), "big")
        return rsa.RSAPublicNumbers(e, n).public_key()
    if kty == "EC":
        if jwk.get("crv") != "P-256":
            raise ValueError("Unsupported EC crv")
        x = int.from_bytes(b64url_decode(jwk["x"]), "big")
        y = int.from_bytes(b64url_decode(jwk["y"]), "big")
        return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    raise ValueError("Unsupported JWK")

def verify_sig(message: bytes, sig_obj: dict, jwks: dict) -> bool:
    kid = sig_obj.get("kid")
    alg = sig_obj.get("alg")
    sig_b64 = sig_obj.get("sig")
    if not kid or not alg or not sig_b64:
        return False
    jwk = next((k for k in (jwks.get("keys") or []) if k.get("kid")==kid), None)
    if not jwk:
        return False
    pub = jwk_to_public_key(jwk)
    sig_raw = b64url_decode(sig_b64)
    try:
        if alg in ("dev_ed25519", "EdDSA", "ed25519"):
            pub.verify(sig_raw, message)
            return True
        if isinstance(alg, str) and alg.startswith("aws_kms:"):
            if isinstance(pub, rsa.RSAPublicKey):
                pub.verify(sig_raw, message, asy_padding.PKCS1v15(), hashes.SHA256())
                return True
            if isinstance(pub, ec.EllipticCurvePublicKey):
                pub.verify(sig_raw, message, ec.ECDSA(hashes.SHA256()))
                return True
        return False
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--attestation", required=True)
    ap.add_argument("--public-keys", required=True)
    args = ap.parse_args()

    asset = Path(args.asset)
    attp = Path(args.attestation)
    pkp = Path(args.public_keys)
    if not asset.exists() or not attp.exists() or not pkp.exists():
        print("FAIL: missing asset/attestation/public-keys")
        return 2

    att = json.loads(attp.read_text(encoding="utf-8"))
    jwks = json.loads(pkp.read_text(encoding="utf-8"))
    digest = sha256_file(asset)
    if att.get("sha256") != digest:
        print("FAIL: sha256 mismatch")
        return 2

    ok = verify_sig(digest.encode("ascii"), att.get("signature") or {}, jwks)
    print("OK" if ok else "FAIL")
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
