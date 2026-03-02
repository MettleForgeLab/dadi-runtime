import os, json, base64, time, hmac, hashlib, argparse

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--scope", default="artifact:read_bytes")
    ap.add_argument("--secret", default=os.getenv("DADI_JWT_HS256_SECRET","dev-secret"))
    ap.add_argument("--ttl", type=int, default=3600)
    args = ap.parse_args()

    token = make_jwt(args.secret, {"tenant_id": args.tenant, "scope": args.scope, "exp": int(time.time()) + args.ttl})
    print(token)

if __name__ == "__main__":
    main()
