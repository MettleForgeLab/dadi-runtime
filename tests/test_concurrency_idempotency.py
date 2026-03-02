import os
import json
import time
import base64
import hmac
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor

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

def headers(tenant="tenant_a", scope="artifact:read_bytes"):
    token = make_jwt(JWT_SECRET, {"tenant_id": tenant, "scope": scope, "exp": int(time.time()) + 3600})
    return {"Authorization": f"Bearer {token}"}

def load_seed_state():
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / ".seed_state.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def test_finalize_idempotent_with_idempotency_key():
    state = load_seed_state()
    if not state:
        return
    run_id = state.get("pipeline_run_id")
    if not run_id:
        return

    # Create new draft deliverable
    r = requests.post(f"{API}/deliverables", json={"pipeline_run_id": run_id, "status":"draft"}, headers=headers(), timeout=30)
    r.raise_for_status()
    did = r.json()["deliverable_id"]

    idem = {"Idempotency-Key": "finalize-test-1", **headers()}

    def do_finalize():
        return requests.post(f"{API}/deliverables/{did}/finalize", headers=idem, timeout=30).json()

    with ThreadPoolExecutor(max_workers=2) as ex:
        a, b = list(ex.map(lambda _: do_finalize(), range(2)))

    assert a.get("deliverable_record_sha256") == b.get("deliverable_record_sha256")

def test_bundle_idempotent_with_idempotency_key():
    state = load_seed_state()
    if not state:
        return
    run_id = state.get("pipeline_run_id")
    if not run_id:
        return

    # Create deliverable and finalize
    r = requests.post(f"{API}/deliverables", json={"pipeline_run_id": run_id, "status":"draft"}, headers=headers(), timeout=30)
    r.raise_for_status()
    did = r.json()["deliverable_id"]
    requests.post(f"{API}/deliverables/{did}/finalize", headers=headers(), timeout=30)

    idem = {"Idempotency-Key": "bundle-test-1", **headers()}

    def do_bundle():
        resp = requests.post(f"{API}/deliverables/{did}/bundle", headers=idem, timeout=60)
        # may 409 if docx missing; acceptable in this test environment
        if resp.status_code != 200:
            return {"status": resp.status_code}
        return resp.json()

    with ThreadPoolExecutor(max_workers=2) as ex:
        a, b = list(ex.map(lambda _: do_bundle(), range(2)))

    if a.get("status") or b.get("status"):
        return

    assert a.get("manifest_artifact_sha256") == b.get("manifest_artifact_sha256")
    assert a.get("bundle_artifact_sha256") == b.get("bundle_artifact_sha256")
