#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
def main():
    root = Path(__file__).resolve().parents[1]
    kr=root/"KEY_REVOCATIONS.json"; ra=root/"REVOCATION_AUTHORITY_PUBLIC_KEYS.json"
    if not kr.exists() or not ra.exists():
        print("FAIL: missing KEY_REVOCATIONS.json or REVOCATION_AUTHORITY_PUBLIC_KEYS.json"); return 2
    feed={"schema_version":"revocation_feed-v1","updated_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
          "serial":int(datetime.now(timezone.utc).timestamp()),
          "revocations":json.loads(kr.read_text(encoding="utf-8")),
          "revocation_authority_public_keys":json.loads(ra.read_text(encoding="utf-8")),
          "signature":None}
    (root/"REVOCATION_FEED.json").write_text(json.dumps(feed,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("Wrote REVOCATION_FEED.json"); return 0
if __name__=="__main__":
    raise SystemExit(main())
