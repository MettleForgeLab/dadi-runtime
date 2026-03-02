\
import os
import json
import argparse
import base64
import hashlib
import hmac
import zipfile
import io
import requests

API_BASE = (os.getenv("NEXT_PUBLIC_API_BASE") or "http://localhost:8000").rstrip("/")
AUTH_TOKEN = os.getenv("NEXT_PUBLIC_AUTH_TOKEN", "").strip()

def canonical_json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def verify_signature(manifest: dict) -> dict:
    sig = manifest.get("signature")
    if not isinstance(sig, dict):
        return {"ok": False, "reason": "missing signature object"}

    alg = sig.get("alg")
    kid = sig.get("kid")
    sig_b64 = sig.get("sig")
    if not (isinstance(alg, str) and isinstance(kid, str) and isinstance(sig_b64, str)):
        return {"ok": False, "reason": "invalid signature fields"}

    unsigned = dict(manifest)
    unsigned.pop("signature", None)
    msg = canonical_json_bytes(unsigned)
    sig_raw = b64url_decode(sig_b64)

    if alg == "hmac-sha256":
        raw = os.getenv("DADI_HMAC_SECRETS_JSON", "").strip()
        if raw:
            keys = json.loads(raw)
            key_b64 = keys.get(kid)
            if not key_b64:
                return {"ok": False, "reason": f"missing hmac key for kid {kid}"}
            key = b64url_decode(key_b64)
        else:
            secret = os.getenv("DADI_BUNDLE_SIGNING_SECRET", "").encode("utf-8")
            if not secret:
                return {"ok": False, "reason": "missing hmac secret"}
            key = secret

        expected = hmac.new(key, msg, hashlib.sha256).digest()
        return {"ok": hmac.compare_digest(expected, sig_raw), "alg": alg, "kid": kid}

    if alg == "ed25519":
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        except Exception:
            return {"ok": False, "reason": "cryptography not installed for ed25519"}
        keys_raw = os.getenv("DADI_ED25519_PUBLIC_KEYS_JSON", "").strip()
        if not keys_raw:
            return {"ok": False, "reason": "missing DADI_ED25519_PUBLIC_KEYS_JSON"}
        keys = json.loads(keys_raw)
        pub_b64 = keys.get(kid)
        if not pub_b64:
            return {"ok": False, "reason": f"missing public key for kid {kid}"}
        pub = b64url_decode(pub_b64)
        if len(pub) != 32:
            return {"ok": False, "reason": "invalid public key length"}
        pk = Ed25519PublicKey.from_public_bytes(pub)
        try:
            pk.verify(sig_raw, msg)
            return {"ok": True, "alg": alg, "kid": kid}
        except Exception:
            return {"ok": False, "alg": alg, "kid": kid, "reason": "verify failed"}

    return {"ok": False, "reason": f"unsupported alg {alg}"}

def download_bundle_bytes(bundle_sha: str) -> bytes:
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    r = requests.get(f"{API_BASE}/artifacts/{bundle_sha}/content", headers=headers, timeout=60)
    r.raise_for_status()
    return r.content

def verify_closure_via_gateway(manifest: dict) -> dict:
    # Optional: verify closure_mode by querying gateway run artifacts
    try:
        closure_mode = manifest.get("closure_mode")
        run_id = manifest.get("pipeline_run_id")
        if not closure_mode or not run_id:
            return {"ok": True, "skipped": True, "reason": "missing closure_mode or pipeline_run_id"}

        headers = {}
        if AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

        r = requests.get(f"{API_BASE}/runs/{run_id}/artifacts", headers=headers, timeout=30)
        if not r.ok:
            return {"ok": True, "skipped": True, "reason": f"gateway artifacts lookup failed: {r.status_code}"}

        expected = set(r.json().get("artifacts", []))
        listed = set()
        for a in manifest.get("artifacts", []) or []:
            if isinstance(a, dict) and isinstance(a.get("sha256"), str):
                listed.add(a["sha256"])

        missing = sorted(list(expected - listed))
        extra = sorted(list(listed - expected))

        return {"ok": len(missing) == 0, "closure_mode": closure_mode, "missing_expected_artifacts": missing, "extra_manifest_artifacts": extra}
    except Exception as e:
        return {"ok": True, "skipped": True, "reason": str(e)}

def verify_zip(bundle_bytes: bytes) -> dict:
    zf = zipfile.ZipFile(io.BytesIO(bundle_bytes), "r")
    names = zf.namelist()
    if "manifest.json" not in names:
        return {"ok": False, "reason": "manifest.json missing from zip"}

    manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
    expected = set()
    for a in manifest.get("artifacts", []) or []:
        if isinstance(a, dict) and isinstance(a.get("sha256"), str):
            expected.add(a["sha256"])

    zip_artifacts = {n.split("/",1)[1] for n in names if n.startswith("artifacts/")}
    missing_in_zip = sorted(list(expected - zip_artifacts))

    mismatches = []
    missing_in_manifest = []
    for n in names:
        if not n.startswith("artifacts/"):
            continue
        sha = n.split("/",1)[1]
        data = zf.read(n)
        h = hashlib.sha256(data).hexdigest()
        if h != sha:
            mismatches.append({"entry": n, "computed": h, "expected": sha})
        if sha not in expected:
            missing_in_manifest.append(sha)

    sig_check = verify_signature(manifest)
    closure_check = verify_closure_via_gateway(manifest)

    ok = (len(mismatches) == 0 and len(missing_in_manifest) == 0 and len(missing_in_zip) == 0 and sig_check.get("ok") is True and closure_check.get("ok") is True)

    return {
        "ok": ok,
        "signature": sig_check,
        "closure": closure_check,
        "missing_in_zip": missing_in_zip,
        "missing_in_manifest": sorted(list(set(missing_in_manifest))),
        "mismatches": mismatches,
        "manifest": manifest,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-sha", help="bundle artifact sha256 (download from gateway)")
    ap.add_argument("--bundle-zip", help="path to local bundle zip")
    ap.add_argument("--out", required=True, help="output report json path")
    args = ap.parse_args()

    if not args.bundle_sha and not args.bundle_zip:
        raise SystemExit("Provide --bundle-sha or --bundle-zip")

    if args.bundle_zip:
        bundle_bytes = open(args.bundle_zip, "rb").read()
        source = {"bundle_zip": args.bundle_zip}
    else:
        bundle_bytes = download_bundle_bytes(args.bundle_sha)
        source = {"bundle_sha256": args.bundle_sha, "api_base": API_BASE}

    report = verify_zip(bundle_bytes)
    report["source"] = source

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\\n")

    if not report.get("ok"):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
