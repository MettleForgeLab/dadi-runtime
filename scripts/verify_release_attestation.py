#!/usr/bin/env python3
import json, base64, hashlib
from pathlib import Path

def b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def main():
    root = Path(__file__).resolve().parents[1]
    mpath = root / "RELEASE_MANIFEST.json"
    apath = root / "RELEASE_ATTESTATION.json"
    if not mpath.exists() or not apath.exists():
        print(json.dumps({"ok": False, "error":"missing files"}, indent=2))
        return 2

    mbytes = mpath.read_bytes()
    msha = hashlib.sha256(mbytes).hexdigest()
    att = json.loads(apath.read_text(encoding="utf-8"))
    if att.get("schema_version") != "release_attestation-v1":
        print(json.dumps({"ok": False, "error":"bad schema_version"}, indent=2))
        return 2
    if att.get("manifest_sha256") != msha:
        print(json.dumps({"ok": False, "error":"manifest_sha256 mismatch", "expected": msha, "got": att.get("manifest_sha256")}, indent=2))
        return 2

    sig = att.get("signature") or {}
    alg = sig.get("alg")
    if alg == "ed25519":
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pk_b64 = sig.get("public_key_b64url")
            s_b64 = sig.get("sig")
            if not pk_b64 or not s_b64:
                raise ValueError("missing public_key_b64url or sig")
            pk = Ed25519PublicKey.from_public_bytes(b64url_decode(pk_b64))
            pk.verify(b64url_decode(s_b64), mbytes)
            print(json.dumps({"ok": True, "alg": alg, "kid": sig.get("kid")}, indent=2))
            return 0
        except Exception as e:
            print(json.dumps({"ok": False, "alg": alg, "error": str(e)}, indent=2))
            return 2

    # Provider-style signature verification can be implemented later.
    print(json.dumps({"ok": False, "error":"unsupported alg", "alg": alg}, indent=2))
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
