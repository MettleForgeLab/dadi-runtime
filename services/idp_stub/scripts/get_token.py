import os
import requests
import json
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--sub", default="dev-user")
    ap.add_argument("--idp-url", default=os.getenv("IDP_URL", "http://localhost:9000"))
    args = ap.parse_args()

    idp = args.idp_url.rstrip("/")
    r = requests.post(f"{idp}/token", json={
      "tenant_id": args.tenant,
      "scope": args.scope,
      "sub": args.sub
    })
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    main()
