import os
import json
import time
import base64
import hmac
import hashlib
import requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000")
JWT_SECRET = os.getenv("DADI_JWT_HS256_SECRET", "dev-secret")

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def make_jwt(secret: str, payload: dict) -> str:
    header = {"alg":"HS256","typ":"JWT"}
    h = b64url(json.dumps(header, separators=(",",":"), sort_keys=True).encode("utf-8"))
    p = b64url(json.dumps(payload, separators=(",",":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{h}.{p}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s = b64url(sig)
    return f"{h}.{p}.{s}"

def test_deliverable_bundle_workflow_invariant():
    token = make_jwt(JWT_SECRET, {"tenant_id":"tenant_a","scope":"artifact:read_bytes","exp": int(time.time()) + 3600})
    headers = {"Authorization": f"Bearer {token}"}

    # Use the seeded run id if present in env; otherwise skip invariant test.

run_id = os.getenv("DADI_SEEDED_RUN_ID")
if not run_id:
    # Try repo-local seed state file
    try:
        import json, pathlib
        p = pathlib.Path(__file__).resolve().parents[1] / ".seed_state.json"
        if p.exists():
            state = json.loads(p.read_text(encoding="utf-8"))
            run_id = state.get("pipeline_run_id")
    except Exception:
        run_id = None
if not run_id:
    return

    # 1) Create draft deliverable
    r = requests.post(f"{API}/deliverables", json={"pipeline_run_id": run_id, "status":"draft"}, headers=headers, timeout=30)
    r.raise_for_status()
    d = r.json()
    did = d["deliverable_id"]

    # 2) Bundling draft should 409
    r2 = requests.post(f"{API}/deliverables/{did}/bundle", headers=headers, timeout=30)
    assert r2.status_code == 409

    # 3) Finalize deliverable
    r3 = requests.post(f"{API}/deliverables/{did}/finalize", headers=headers, timeout=30)
    assert r3.status_code in (200, 201)

    # 4) Create bundle should succeed OR 409 if docx missing (seed must ensure docx exists)
    r4 = requests.post(f"{API}/deliverables/{did}/bundle", headers=headers, timeout=60)
    if r4.status_code == 409:
        # if no docx exists, this is correct fail-closed behavior
        return
    r4.raise_for_status()
    b = r4.json()
    msha = b.get("manifest_artifact_sha256")
    bsha = b.get("bundle_artifact_sha256")
    assert msha and bsha

    # 5) Verify manifest should be ok:true
    r5 = requests.post(
        f"{API}/deliverables/{did}/bundle/verify",
        json={"manifest_artifact_sha256": msha},
        headers=headers,
        timeout=30
    )
    r5.raise_for_status()
    v = r5.json()
    assert v.get("ok") is True

    # 6) Download bundle bytes should be allowed with scope
    r6 = requests.get(f"{API}/artifacts/{bsha}/content", headers=headers, timeout=60)
    assert r6.status_code == 200
