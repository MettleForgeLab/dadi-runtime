\
#!/usr/bin/env python3
import argparse
import json
import hashlib
from pathlib import Path
import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as asy_padding

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def verify_manifest(release_dir: Path) -> dict:
    mpath = release_dir / "RELEASE_MANIFEST.json"
    if not mpath.exists():
        return {"ok": False, "error": "RELEASE_MANIFEST.json missing"}
    m = json.loads(mpath.read_text(encoding="utf-8"))
    hashes_map = m.get("critical_file_hashes") or {}

    missing, mismatched = [], []
    for rel, expected in hashes_map.items():
        p = release_dir / rel
        if not p.exists():
            missing.append(rel)
            continue
        got = sha256_file(p)
        if got != expected:
            mismatched.append({"path": rel, "expected": expected, "got": got})

    items = [f"{hashes_map[k]}  {k}" for k in sorted(hashes_map.keys())]
    tree = hashlib.sha256(("\n".join(items) + "\n").encode("utf-8")).hexdigest()
    tree_ok = tree == m.get("tree_sha256")

    ok = (len(missing) == 0 and len(mismatched) == 0 and tree_ok)
    return {"ok": ok, "missing_files": missing, "mismatched_files": mismatched, "tree_ok": tree_ok}

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

def verify_attestation(release_dir: Path, jwks: dict) -> dict:
    apath = release_dir / "RELEASE_ATTESTATION.json"
    mpath = release_dir / "RELEASE_MANIFEST.json"
    if not apath.exists():
        return {"ok": False, "error": "RELEASE_ATTESTATION.json missing"}
    if not mpath.exists():
        return {"ok": False, "error": "RELEASE_MANIFEST.json missing"}

    att = json.loads(apath.read_text(encoding="utf-8"))
    sig = att.get("signature") or {}
    kid, alg, sig_b64 = sig.get("kid"), sig.get("alg"), sig.get("sig")
    if not kid or not alg or not sig_b64:
        return {"ok": False, "error": "signature fields missing"}

    manifest_bytes = mpath.read_bytes()
    msha = hashlib.sha256(manifest_bytes).hexdigest()
    if att.get("manifest_sha256") != msha:
        return {"ok": False, "error": "manifest_sha256 mismatch"}

    jwk = next((k for k in (jwks.get("keys") or []) if k.get("kid") == kid), None)
    if not jwk:
        return {"ok": False, "error": "public key not found", "kid": kid}

    pub = jwk_to_public_key(jwk)
    sig_raw = b64url_decode(sig_b64)

    try:
        if alg in ("dev_ed25519", "EdDSA", "ed25519"):
            pub.verify(sig_raw, manifest_bytes)
            return {"ok": True, "kid": kid, "alg": alg}
        if alg.startswith("aws_kms:"):
            if isinstance(pub, rsa.RSAPublicKey):
                pub.verify(sig_raw, manifest_bytes, asy_padding.PKCS1v15(), hashes.SHA256())
                return {"ok": True, "kid": kid, "alg": alg}
            if isinstance(pub, ec.EllipticCurvePublicKey):
                pub.verify(sig_raw, manifest_bytes, ec.ECDSA(hashes.SHA256()))
                return {"ok": True, "kid": kid, "alg": alg}
            return {"ok": False, "error": "unsupported key type"}
        return {"ok": False, "error": "unsupported alg"}
    except Exception as e:
        return {"ok": False, "error": "verify failed", "detail": str(e)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release-dir", required=True)
    ap.add_argument("--public-keys", required=True)
    args = ap.parse_args()

    release_dir = Path(args.release_dir)
    jwks = json.loads(Path(args.public_keys).read_text(encoding="utf-8"))

    m = verify_manifest(release_dir)
    a = verify_attestation(release_dir, jwks)
    # Check release status if present
status_path = release_dir / "RELEASE_STATUS.json"
status = None
if status_path.exists():
    status = json.loads(status_path.read_text(encoding="utf-8"))

    ok = m.get("ok") is True and a.get("ok") is True and (not status or status.get("status") == "active")
    print(json.dumps({"ok": ok, "manifest": m, "attestation": a, "status": status}, indent=2))
    raise SystemExit(0 if ok else 2)

if __name__ == "__main__":
    main()
