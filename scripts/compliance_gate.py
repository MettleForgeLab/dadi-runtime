#!/usr/bin/env python3
import os
import json
import requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000").rstrip("/")

def main():
    url = f"{API}/health/compliance?strict=true"
    try:
        r = requests.get(url, timeout=10)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e), "url": url}, indent=2))
        return 2

    if not r.ok:
        print(json.dumps({"ok": False, "status_code": r.status_code, "body": r.text[:2000], "url": url}, indent=2))
        return 2

    data = r.json()
    if data.get("ok") is True:
        print(json.dumps({"ok": True, "url": url}, indent=2))
        return 0

    print(json.dumps({"ok": False, "url": url, "failures": data.get("failures"), "snapshot": data}, indent=2))
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
