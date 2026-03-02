#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from datetime import datetime

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reason", required=True)
    ap.add_argument("--superseded-by", default=None)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    spath = root / "RELEASE_STATUS.json"
    if not spath.exists():
        print("FAIL: RELEASE_STATUS.json missing")
        return 2

    s = json.loads(spath.read_text(encoding="utf-8"))
    s["status"] = "revoked"
    s["revoked_reason"] = args.reason
    if args.superseded_by:
        s["superseded_by"] = args.superseded_by
    s["updated_at_utc"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    spath.write_text(json.dumps(s, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Release marked revoked")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
