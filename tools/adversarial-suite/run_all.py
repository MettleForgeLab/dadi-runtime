#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)

def check_baseline(work: Path) -> bool:
    r = sh(["python", "scripts/verify_release_manifest.py"], cwd=work)
    return r.returncode == 0

def check_tamper_manifest_detected(work: Path) -> bool:
    mpath = work / "RELEASE_MANIFEST.json"
    b = bytearray(mpath.read_bytes())
    b[0] = (b[0] + 1) % 256
    mpath.write_bytes(bytes(b))
    r = sh(["python", "scripts/verify_release_manifest.py"], cwd=work)
    return r.returncode != 0

def check_key_mismatch_detected(work: Path) -> bool:
    pk = work / "RELEASE_PUBLIC_KEYS.json"
    if not pk.exists():
        return True
    pk.write_text(json.dumps({"keys": []}, indent=2) + "\n", encoding="utf-8")
    r = sh(["python", "tools/release-verifier/verify_release.py", "--release-dir", ".", "--public-keys", "RELEASE_PUBLIC_KEYS.json"], cwd=work)
    return r.returncode != 0

def check_sql_drift_detected(work: Path) -> bool:
    cpath = work / "services" / "gateway" / "migrations" / "checksums.json"
    sqlp = work / "services" / "gateway" / "sql" / "schema.sql"
    if not cpath.exists() or not sqlp.exists():
        return True
    checks = json.loads(cpath.read_text(encoding="utf-8"))
    expected = checks.get("schema.sql")
    if not expected:
        return True
    b = bytearray(sqlp.read_bytes())
    b[0] = (b[0] + 1) % 256
    import hashlib
    drift = hashlib.sha256(bytes(b)).hexdigest()
    return drift != expected

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release-dir", required=True)
    ap.add_argument("--mode", choices=["expect_success", "expect_failure"], default="expect_failure")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    release_dir = Path(args.release_dir).resolve()
    if not (release_dir / "RELEASE_MANIFEST.json").exists():
        print("FAIL: missing RELEASE_MANIFEST.json")
        return 2

    report = {"ok": False, "mode": args.mode, "checks": {}}

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        work = td / "release"

        def fresh():
            if work.exists():
                shutil.rmtree(work)
            shutil.copytree(release_dir, work)

        fresh()
        baseline_ok = check_baseline(work)
        report["checks"]["baseline_verifies"] = baseline_ok

        fresh()
        report["checks"]["tamper_manifest_detected"] = check_tamper_manifest_detected(work)

        fresh()
        report["checks"]["key_mismatch_detected"] = check_key_mismatch_detected(work)

        fresh()
        report["checks"]["sql_drift_detected"] = check_sql_drift_detected(work)

    if args.mode == "expect_success":
        report["ok"] = bool(report["checks"]["baseline_verifies"])
    else:
        report["ok"] = bool(
            report["checks"]["baseline_verifies"]
            and report["checks"]["tamper_manifest_detected"]
            and report["checks"]["key_mismatch_detected"]
            and report["checks"]["sql_drift_detected"]
        )

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
