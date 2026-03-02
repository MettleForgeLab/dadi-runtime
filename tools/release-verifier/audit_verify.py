#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)

def run(cmd, cwd, name):
    r = sh(cmd, cwd=cwd)
    return {"name": name, "cmd": " ".join(cmd), "exit_code": r.returncode, "stdout_tail": r.stdout[-2000:], "stderr_tail": r.stderr[-2000:]}

def check_key_revocations_authority(rd: Path, jwks_release: dict, signing_kid: str) -> tuple[bool, dict, str]:
    kr = rd / "KEY_REVOCATIONS.json"
    if not kr.exists():
        return True, {"present": False}, "not present"
    ra = rd / "REVOCATION_AUTHORITY_PUBLIC_KEYS.json"
    if not ra.exists():
        return False, {}, "REVOCATION_AUTHORITY_PUBLIC_KEYS.json missing"
    try:
        ra_obj = load_json(ra)
        jwks_auth = {"keys": ra_obj.get("keys") or []} if isinstance(ra_obj, dict) else {"keys": []}
    except Exception as e:
        return False, {}, f"revocation authority keys parse error: {e}"
    try:
        obj = load_json(kr)
    except Exception as e:
        return False, {}, f"parse error: {e}"
    sig = obj.get("signature")
    if not isinstance(sig, dict):
        return False, {}, "signature missing"
    unsigned = dict(obj)
    unsigned["signature"] = None
    unsigned.pop("payload_sha256", None)
    unsigned.pop("signed_at_utc", None)
    msg = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ok_sig, msg_sig = verify_signature(msg, sig, jwks_auth)
    if not ok_sig:
        return False, {"sig_error": msg_sig}, "signature invalid"
    revoked = obj.get("revoked_kids") or []
    for r in revoked:
        if isinstance(r, dict) and r.get("kid") == signing_kid:
            return False, {"revoked_kid": signing_kid, "entry": r}, "signing kid revoked"
        if isinstance(r, str) and r == signing_kid:
            return False, {"revoked_kid": signing_kid}, "signing kid revoked"
    return True, {"present": True, "revoked_kids_count": len(revoked)}, "ok"


def maybe_update_revocations_from_feed(rd: Path, feed_url: str | None, offline: bool, require_fresh: bool, max_age_hours: int | None) -> tuple[bool, str]:
    if offline or not feed_url:
        return True, "offline"
    import json as _json
    import urllib.request
    from datetime import datetime, timezone

    try:
        with urllib.request.urlopen(feed_url, timeout=10) as resp:
            raw = resp.read()
        feed = _json.loads(raw.decode("utf-8"))

        # Optional freshness check
        if max_age_hours is not None:
            ts = feed.get("updated_at_utc") or feed.get("signed_at_utc")
            if isinstance(ts, str):
                try:
                    # accept both with and without trailing Z
                    ts_norm = ts.replace("Z", "")
                    dt = datetime.fromisoformat(ts_norm)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
                    if age_h > float(max_age_hours):
                        if require_fresh:
                            return False, f"feed too old: {age_h:.2f}h > {max_age_hours}h"
                except Exception:
                    if require_fresh:
                        return False, "feed timestamp parse failed"
            else:
                if require_fresh:
                    return False, "feed missing updated_at_utc"

        # Materialize feed components for downstream checks
        (rd/"REVOCATION_FEED.json").write_text(_json.dumps(feed, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        (rd/"KEY_REVOCATIONS.json").write_text(_json.dumps(feed.get("revocations") or {}, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        (rd/"REVOCATION_AUTHORITY_PUBLIC_KEYS.json").write_text(_json.dumps(feed.get("revocation_authority_public_keys") or {}, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        return True, "feed"
    except Exception as e:
        if require_fresh:
            return False, f"feed fetch failed: {e}"
        return True, f"feed unavailable; using local ({e})"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release-dir", required=True)
    ap.add_argument("--public-keys", default=None, help="Path to RELEASE_PUBLIC_KEYS.json (defaults to release-dir/RELEASE_PUBLIC_KEYS.json)")
    ap.add_argument("--allow-revoked", action="store_true")
    ap.add_argument("--out", default="audit_report.json")
    ap.add_argument("--revocation-feed-url", default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--require-fresh-revocations", action="store_true")
    ap.add_argument("--profile", choices=["archival","procurement"], default="archival")
    ap.add_argument("--max-feed-age-hours", type=int, default=None)
    args = ap.parse_args()

    # Profile policy
    if args.profile == "procurement":
        args.require_fresh_revocations = True
        if not args.revocation_feed_url:
            print("FAIL: procurement profile requires --revocation-feed-url")
            return 2

    rd = Path(args.release_dir).resolve()
    if not rd.exists():
        print("FAIL: release-dir not found")
        return 2

    pubkeys = Path(args.public_keys).resolve() if args.public_keys else (rd / "RELEASE_PUBLIC_KEYS.json")

    report = {"ok": False, "release_dir": str(rd), "checks": []}

    # 1) Release status
    status_path = rd / "RELEASE_STATUS.json"
    status = None
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except Exception:
            status = {"status": "unknown_parse_error"}
        if not args.allow_revoked and status.get("status") != "active":
            report["checks"].append({"name": "release_status_active", "ok": False, "status": status})
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
            return 2
        report["checks"].append({"name": "release_status_active", "ok": True, "status": status})
    else:
        report["checks"].append({"name": "release_status_present", "ok": False, "error": "RELEASE_STATUS.json missing"})
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    # 2) Verify release manifest hashes
    report["checks"].append(run(["python", "scripts/verify_release_manifest.py"], rd, "verify_release_manifest"))
    if report["checks"][-1]["exit_code"] != 0:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    # 3) Verify release attestation signature (internal)
    report["checks"].append(run(["python", "scripts/verify_release_attestation.py"], rd, "verify_release_attestation"))
    if report["checks"][-1]["exit_code"] != 0:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    # 4) Verify SBOM contract
    if (rd / "scripts" / "verify_sbom.py").exists():
        report["checks"].append(run(["python", "scripts/verify_sbom.py"], rd, "verify_sbom"))
        if report["checks"][-1]["exit_code"] != 0:
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
            return 2
    else:
        report["checks"].append({"name": "verify_sbom", "ok": False, "error": "verify_sbom.py missing"})
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    # 5) Verify provenance signature + contract
    report["checks"].append(run(["python", "scripts/verify_provenance.py"], rd, "verify_provenance"))
    if report["checks"][-1]["exit_code"] != 0:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    report["checks"].append(run(["python", "scripts/verify_provenance_contract.py"], rd, "verify_provenance_contract"))
    if report["checks"][-1]["exit_code"] != 0:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    # 6) External verifier (standalone)
    if not pubkeys.exists():
        report["checks"].append({"name": "public_keys_present", "ok": False, "error": f"{pubkeys} missing"})
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2
    report["checks"].append(run(["python", "tools/release-verifier/verify_release.py", "--release-dir", ".", "--public-keys", str(pubkeys)], rd, "external_verify_release"))
    if report["checks"][-1]["exit_code"] != 0:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    # 7) Adversarial suite (expect_failure)
    adv = rd / "tools" / "adversarial-suite" / "run_all.py"
    if adv.exists():
        report["checks"].append(run(["python", "tools/adversarial-suite/run_all.py", "--release-dir", ".", "--mode", "expect_failure", "--out", "adversarial_report.json"], rd, "adversarial_suite"))
        if report["checks"][-1]["exit_code"] != 0:
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
            return 2
    else:
        report["checks"].append({"name": "adversarial_suite", "ok": False, "error": "adversarial suite missing"})
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    report["ok"] = True
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
