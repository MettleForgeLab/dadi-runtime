"""Safe fixture export: manifest-only

This script exports only:
- fixture_manifest.json
- no artifact bytes

Use this when you need to share provenance and drift localization under NDA constraints.

Inputs:
- A fixture directory or zip created by the regression harness.

Output:
- A zip containing only fixture_manifest.json (plus a small export note).
"""

from __future__ import annotations

import os, json, zipfile
import argparse

MANIFEST = "fixture_manifest.json"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True, help="Fixture directory or zip")
    ap.add_argument("--out", required=True, help="Output zip path")
    args = ap.parse_args()

    manifest_data = None

    if os.path.isdir(args.fixture):
        p = os.path.join(args.fixture, MANIFEST)
        with open(p, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    else:
        with zipfile.ZipFile(args.fixture, "r") as z:
            with z.open(MANIFEST) as f:
                manifest_data = json.loads(f.read().decode("utf-8"))

    note = {
        "export_mode": "manifest-only",
        "bytes_exported": False,
        "note": "This export contains no artifact bytes. It preserves only structural provenance metadata."
    }

    with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, json.dumps(manifest_data, indent=2, sort_keys=True) + "\n")
        z.writestr("EXPORT_NOTE.json", json.dumps(note, indent=2, sort_keys=True) + "\n")

if __name__ == "__main__":
    main()
