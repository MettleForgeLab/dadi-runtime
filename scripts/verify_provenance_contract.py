#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    root = Path(__file__).resolve().parents[1]
    prov_p = root / "PROVENANCE.json"
    if not prov_p.exists():
        print("FAIL: PROVENANCE.json missing")
        return 2
    prov = json.loads(prov_p.read_text(encoding="utf-8"))

    version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root/"VERSION").exists() else None
    if version and prov.get("version") != version:
        print("FAIL: provenance version mismatch")
        return 2

    src = prov.get("source") or {}
    for k in ("repo","ref","sha"):
        if k not in src:
            print("FAIL: provenance source missing", k)
            return 2

    digests = prov.get("artifact_digests_sha256") or {}
    required_files = ["RELEASE_MANIFEST.json","RELEASE_ATTESTATION.json","RELEASE_PUBLIC_KEYS.json","SBOM.cdx.json","SBOM.spdx.json"]
    missing = [f for f in required_files if f not in digests]
    if missing:
        print("FAIL: provenance missing digests for", missing)
        return 2

    mismatched = []
    for name, expected in digests.items():
        p = root / name
        if not p.exists():
            continue
        got = sha256_file(p)
        if got != expected:
            mismatched.append({"file": name, "expected": expected, "got": got})
    if mismatched:
        print("FAIL: provenance digest mismatch", json.dumps(mismatched, indent=2))
        return 2

    print("OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
