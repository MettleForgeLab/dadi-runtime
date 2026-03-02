#!/usr/bin/env python3
import os
import json
import time
import subprocess
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000").rstrip("/")
IDP = os.getenv("IDP_URL", "http://localhost:9000").rstrip("/")
EVIDENCE = ROOT / "evidence"

def sh(cmd: list[str], check=True):
    return subprocess.run(cmd, check=check, capture_output=True, text=True)

def wait_ok(url: str, timeout_s: int = 90):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            r = requests.get(url, timeout=2)
            if r.ok:
                return True
        except Exception:
            time.sleep(1)
    return False

def mint_token(tenant: str, scope: str):
    r = requests.post(f"{IDP}/token", json={"tenant_id": tenant, "scope": scope, "sub": "smoke"}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]

def fail(report, step, reason, extra=None):
    report["ok"] = False
    report["failed_step"] = step
    report["reason"] = reason
    if extra is not None:
        report["extra"] = extra
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "smoke_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(2)

def main():
    report = {"ok": False, "steps": [], "artifacts": {}}
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    # 1) Start stack
    report["steps"].append({"step": "compose_up"})
    sh(["docker", "compose", "-f", str(ROOT / "deploy/reference/docker-compose.yml"), "up", "--build", "-d"], check=True)

    # 2) Wait services
    if not wait_ok(f"{API}/health", 120):
        fail(report, "wait_gateway", "gateway not healthy")
    if not wait_ok(f"{IDP}/.well-known/jwks.json", 120):
        fail(report, "wait_idp", "idp not healthy")
    report["steps"].append({"step": "wait_services", "ok": True})

    # 3) Mint tokens
    token_a = mint_token("tenant_a", "artifact:read_bytes deliverable:download_bundle deliverable:evidence deliverable:evidence_download")
    token_b = mint_token("tenant_b", "artifact:read_bytes")
    report["artifacts"]["token_a_prefix"] = token_a[:24]
    report["artifacts"]["token_b_prefix"] = token_b[:24]

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 4) Run seed script (should write .seed_state.json)
    report["steps"].append({"step": "seed_demo"})
    env = os.environ.copy()
    env["API_BASE"] = API
    env["IDP_URL"] = IDP
    env["DATABASE_URL"] = env.get("DATABASE_URL", "postgresql://dadi:dadi@localhost:5432/dadi")
    r = subprocess.run(["python", str(ROOT / "deploy/reference/scripts/seed_demo.py")], env=env, capture_output=True, text=True)
    report["artifacts"]["seed_stdout_tail"] = r.stdout[-3000:]
    report["artifacts"]["seed_stderr_tail"] = r.stderr[-3000:]
    if r.returncode != 0:
        fail(report, "seed_demo", "seed script failed", {"returncode": r.returncode})

    seed_state_path = ROOT / ".seed_state.json"
    if not seed_state_path.exists():
        fail(report, "seed_state", ".seed_state.json missing")

    state = json.loads(seed_state_path.read_text(encoding="utf-8"))
    report["artifacts"]["seed_state"] = state

    did = state.get("deliverable_id")
    bundle_id = state.get("bundle_id")
    bundle_sha = state.get("bundle_artifact_sha256")
    manifest_sha = state.get("manifest_artifact_sha256")
    run_id = state.get("pipeline_run_id")

    if not (did and manifest_sha and bundle_id and bundle_sha and run_id):
        fail(report, "seed_outputs", "seed state missing required ids", state)

    # 5) Verify manifest server-side
    vr = requests.post(
        f"{API}/deliverables/{did}/bundle/verify",
        json={"manifest_artifact_sha256": manifest_sha},
        headers=headers_a,
        timeout=30
    )
    report["steps"].append({"step": "bundle_verify", "status": vr.status_code})
    if not vr.ok:
        fail(report, "bundle_verify", "server verify request failed", {"status": vr.status_code, "body": vr.text[:2000]})

    vj = vr.json()
    report["artifacts"]["server_verify"] = vj
    if vj.get("ok") is not True:
        fail(report, "bundle_verify", "server verify returned ok:false", vj)

    # 6) Ensure deliverable is sent (download policy)
    ms = requests.post(f"{API}/deliverables/{did}/mark_sent", headers=headers_a, timeout=30)
    report["steps"].append({"step": "mark_sent", "status": ms.status_code})

    # 7) Download bundle with correct scope
    dl = requests.get(
        f"{API}/deliverables/{did}/bundles/{bundle_id}/download",
        headers=headers_a,
        timeout=60
    )
    report["steps"].append({"step": "bundle_download", "status": dl.status_code, "bytes": len(dl.content) if dl.ok else 0})
    if not dl.ok:
        fail(report, "bundle_download", "download failed", {"status": dl.status_code, "body": dl.text[:2000]})

    bundle_path = EVIDENCE / "bundle_downloaded.zip"
    bundle_path.write_bytes(dl.content)
    report["artifacts"]["bundle_path"] = str(bundle_path)

    # 8) Offline verify (CLI)
    out_report = EVIDENCE / "bundle_verification_report.json"
    env2 = os.environ.copy()
    env2["NEXT_PUBLIC_API_BASE"] = API
    env2["NEXT_PUBLIC_AUTH_TOKEN"] = token_a
    pr = subprocess.run(
        ["python", str(ROOT / "tools/bundle-verify/bundle_verify.py"), "--bundle-zip", str(bundle_path), "--out", str(out_report)],
        env=env2,
        capture_output=True,
        text=True
    )
    report["artifacts"]["offline_verify_stdout_tail"] = pr.stdout[-2000:]
    report["artifacts"]["offline_verify_stderr_tail"] = pr.stderr[-2000:]
    if pr.returncode != 0 or not out_report.exists():
        fail(report, "offline_verify", "offline verifier failed", {"returncode": pr.returncode})

    ov = json.loads(out_report.read_text(encoding="utf-8"))
    report["artifacts"]["offline_verify"] = ov
    if ov.get("ok") is not True:
        fail(report, "offline_verify", "offline verifier report ok:false", ov)

    # 9) Evidence excerpts: audit + metrics
    ae = requests.get(f"{API}/audit?pipeline_run_id={run_id}&limit=200", headers=headers_a, timeout=30)
    if ae.ok:
        (EVIDENCE / "audit_excerpt.json").write_text(json.dumps(ae.json(), indent=2), encoding="utf-8")
        report["artifacts"]["audit_excerpt_path"] = str(EVIDENCE / "audit_excerpt.json")

        vc = requests.get(f"{API}/audit/verify-chain?pipeline_run_id={run_id}&limit=500", headers=headers_a, timeout=30)
        if vc.ok:
            (EVIDENCE / "audit_chain_verify.json").write_text(json.dumps(vc.json(), indent=2), encoding="utf-8")
            report["artifacts"]["audit_chain_verify_path"] = str(EVIDENCE / "audit_chain_verify.json")

    me = requests.get(f"{API}/runs/{run_id}/metrics", headers=headers_a, timeout=30)
    if me.ok:
        (EVIDENCE / "metrics_excerpt.json").write_text(json.dumps(me.json(), indent=2), encoding="utf-8")
        report["artifacts"]["metrics_excerpt_path"] = str(EVIDENCE / "metrics_excerpt.json")

    report["ok"] = True
    (EVIDENCE / "smoke_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
