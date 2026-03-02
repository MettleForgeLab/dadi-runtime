import os
import json
import time
import base64
import hmac
import hashlib
import io
import zipfile
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

def auth_headers(tenant: str = "tenant_a", scope: str = "artifact:read_bytes"):
    token = make_jwt(JWT_SECRET, {"tenant_id": tenant, "scope": scope, "exp": int(time.time()) + 3600})
    return {"Authorization": f"Bearer {token}"}

def load_seed_state():
    # Repo root .seed_state.json written by seed_demo.py
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / ".seed_state.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def test_tampered_manifest_signature_fails_server_verify():
    state = load_seed_state()
    if not state:
        return
    tenant = state.get("tenant_a", "tenant_a")
    did = state.get("deliverable_id")
    manifest_sha = state.get("manifest_artifact_sha256")
    if not did or not manifest_sha:
        return

    headers = auth_headers(tenant)

    # Fetch manifest bytes via artifacts content
    mbytes = requests.get(f"{API}/artifacts/{manifest_sha}/content", headers=headers, timeout=60).content
    obj = json.loads(mbytes.decode("utf-8"))

    # Tamper: change deliverable_status (breaks signature)
    obj["deliverable_status"] = "sent" if obj.get("deliverable_status") != "sent" else "final"

    tampered = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    # Store tampered manifest as a new artifact
    payload = {
        "meta": {
            "artifact_type": "deliverable/manifest/v1",
            "media_type": "application/json",
            "canonical": True,
            "canonical_format": "json_c14n_v1",
            "schema_version": "deliverable_manifest-v1",
        },
        "content_b64": base64.b64encode(tampered).decode("ascii"),
    }
    r = requests.post(f"{API}/artifacts", json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    tampered_sha = r.json()["sha256"]

    # Verify should return ok:false (signature fails) OR 400 (schema ok but verify false is ok)
    vr = requests.post(
        f"{API}/deliverables/{did}/bundle/verify",
        json={"manifest_artifact_sha256": tampered_sha},
        headers=headers,
        timeout=60
    )
    vr.raise_for_status()
    data = vr.json()
    assert data.get("ok") is False

def test_tampered_bundle_zip_detected_by_offline_verifier():
    state = load_seed_state()
    if not state:
        return
    tenant = state.get("tenant_a", "tenant_a")
    bundle_sha = state.get("bundle_artifact_sha256")
    if not bundle_sha:
        return

    headers = auth_headers(tenant)

    zbytes = requests.get(f"{API}/artifacts/{bundle_sha}/content", headers=headers, timeout=60).content
    zf = zipfile.ZipFile(io.BytesIO(zbytes), "r")

    # Pick one artifact entry and flip a byte
    artifact_names = [n for n in zf.namelist() if n.startswith("artifacts/")]
    if not artifact_names:
        return
    target_name = artifact_names[0]
    target_sha = target_name.split("/", 1)[1]
    data = bytearray(zf.read(target_name))
    if not data:
        return
    data[0] = (data[0] + 1) % 256  # flip one byte

    # Rebuild a tampered zip with same filenames/order
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z2:
        for name in zf.namelist():
            if name == target_name:
                z2.writestr(name, bytes(data))
            else:
                z2.writestr(name, zf.read(name))
    tampered_zip = out.getvalue()

    # Use local verifier function (from tools/bundle-verify)
    # It should fail due to hash mismatch (computed != filename)
    import sys, pathlib
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "tools" / "bundle-verify"))
    import bundle_verify as bv

    report = bv.verify_zip(tampered_zip)
    assert report.get("ok") is False
    assert report.get("mismatches"), "Expected mismatches due to byte flip"
