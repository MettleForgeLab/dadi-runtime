#!/usr/bin/env python3
import json
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root/"VERSION").exists() else None

    cdx_path = root / "SBOM.cdx.json"
    spdx_path = root / "SBOM.spdx.json"

    if not cdx_path.exists() or not spdx_path.exists():
        print("FAIL: SBOM files missing")
        return 2

    try:
        cdx = json.loads(cdx_path.read_text(encoding="utf-8"))
        spdx = json.loads(spdx_path.read_text(encoding="utf-8"))
    except Exception as e:
        print("FAIL: SBOM JSON parse error:", str(e))
        return 2

    if cdx.get("bomFormat") != "CycloneDX":
        print("FAIL: SBOM.cdx.json bomFormat not CycloneDX")
        return 2

    comp = (cdx.get("metadata") or {}).get("component") or {}
    if version and comp.get("version") != version:
        print("FAIL: SBOM.cdx.json component version mismatch")
        return 2

    if not (cdx.get("metadata") or {}).get("timestamp"):
        print("FAIL: SBOM.cdx.json missing metadata.timestamp")
        return 2

    comps = cdx.get("components") or []
    if not isinstance(comps, list):
        print("FAIL: SBOM.cdx.json components must be array")
        return 2

    if not str(spdx.get("spdxVersion","")).startswith("SPDX-"):
        print("FAIL: SBOM.spdx.json spdxVersion invalid")
        return 2

    if not (spdx.get("creationInfo") or {}).get("created"):
        print("FAIL: SBOM.spdx.json missing creationInfo.created")
        return 2

    print("OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
