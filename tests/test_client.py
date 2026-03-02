import os, json, base64, time, hmac, hashlib, requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000")
JWT_SECRET = os.getenv("DADI_JWT_HS256_SECRET", "dev-secret")
TENANT = os.getenv("DADI_TEST_TENANT", "tenant_a")
SCOPES = os.getenv("DADI_TEST_SCOPES", "artifact:read_bytes")

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

def session() -> requests.Session:
    s = requests.Session()
    token = make_jwt(JWT_SECRET, {"tenant_id": TENANT, "scope": SCOPES, "exp": int(time.time()) + 3600})
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s
