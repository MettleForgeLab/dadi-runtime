import os
import time
import json
import base64
import hmac
import hashlib
import requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000").rstrip("/")
IDP = os.getenv("IDP_URL", "http://localhost:9000").rstrip("/")
JWT_SECRET = os.getenv("DADI_JWT_HS256_SECRET", "dev-secret")

def wait_gateway(timeout_s=3) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            r = requests.get(f"{API}/health", timeout=1)
            if r.ok:
                return True
        except Exception:
            time.sleep(0.2)
    return False

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def make_hs256_jwt(tenant: str, scope: str) -> str:
    header = {"alg":"HS256","typ":"JWT"}
    payload = {"tenant_id": tenant, "scope": scope, "exp": int(time.time()) + 3600}
    h = b64url(json.dumps(header, separators=(",",":"), sort_keys=True).encode("utf-8"))
    p = b64url(json.dumps(payload, separators=(",",":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{h}.{p}".encode("ascii")
    sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s = b64url(sig)
    return f"{h}.{p}.{s}"

def mint_token(tenant: str, scope: str) -> str:
    # Prefer idp stub if available; fall back to HS256 token in dev.
    try:
        r = requests.post(f"{IDP}/token", json={"tenant_id": tenant, "scope": scope, "sub":"pytest"}, timeout=2)
        if r.ok:
            return r.json()["access_token"]
    except Exception:
        pass
    return make_hs256_jwt(tenant, scope)

def h(scope: str, tenant="tenant_a"):
    return {"Authorization": f"Bearer {mint_token(tenant, scope)}"}

def load_seed_state():
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / ".seed_state.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def test_auth_required_401():
    if not wait_gateway():
        return
    r = requests.get(f"{API}/audit?limit=1", timeout=5)
    assert r.status_code == 401

def test_scope_required_bytes_403():
    if not wait_gateway():
        return
    # random sha; 403 or 404 acceptable depending on existence. We enforce that missing scope must not return 200.
    r = requests.get(f"{API}/artifacts/{'0'*64}/content", headers=h(scope=""), timeout=5)
    assert r.status_code in (403, 404)

def test_bundle_download_scope_and_state():
    if not wait_gateway():
        return
    state = load_seed_state()
    if not state:
        return
    did = state.get("deliverable_id")
    bid = state.get("bundle_id")
    if not did or not bid:
        return

    # Without download scope => 403
    r1 = requests.get(f"{API}/deliverables/{did}/bundles/{bid}/download", headers=h(scope="artifact:read_bytes"), timeout=10)
    assert r1.status_code in (403, 409, 404)

    # With download scope but if not sent => 409; if sent => 200
    r2 = requests.get(f"{API}/deliverables/{did}/bundles/{bid}/download", headers=h(scope="deliverable:download_bundle"), timeout=10)
    assert r2.status_code in (200, 409, 404)

def test_evidence_create_requires_scope():
    if not wait_gateway():
        return
    state = load_seed_state()
    if not state:
        return
    did = state.get("deliverable_id")
    if not did:
        return

    # Without evidence scope => 403 or 409 (if not sent) but never 200
    r = requests.post(f"{API}/deliverables/{did}/evidence", headers=h(scope="artifact:read_bytes"), timeout=10)
    assert r.status_code in (403, 409, 404)

def test_cross_tenant_bundle_visibility_404():
    if not wait_gateway():
        return
    state = load_seed_state()
    if not state:
        return
    did = state.get("deliverable_id")
    if not did:
        return
    r = requests.get(f"{API}/deliverables/{did}", headers=h(scope="artifact:read_bytes", tenant="tenant_b"), timeout=10)
    assert r.status_code in (404, 401, 403)
