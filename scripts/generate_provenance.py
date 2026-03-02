#!/usr/bin/env python3
import json, os, hashlib
from pathlib import Path
from datetime import datetime, timezone

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    root = Path(__file__).resolve().parents[1]
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    artifacts={}
    for name in ["RELEASE_MANIFEST.json","RELEASE_ATTESTATION.json","RELEASE_PUBLIC_KEYS.json","SBOM.cdx.json","SBOM.spdx.json","RELEASE_STATUS.json"]:
        p=root/name
        if p.exists():
            artifacts[name]=sha256_file(p)
    prov={
      "schema_version":"provenance-v1",
      "created_at_utc": created,
      "version": (root/"VERSION").read_text().strip() if (root/"VERSION").exists() else "unknown",
      "source":{"repo":os.getenv("GITHUB_REPOSITORY","unknown"),"ref":os.getenv("GITHUB_REF","unknown"),"sha":os.getenv("GITHUB_SHA","unknown")},
      "build":{"builder":"GitHub Actions","workflow":os.getenv("GITHUB_WORKFLOW","unknown"),"run_id":os.getenv("GITHUB_RUN_ID","unknown"),"run_attempt":os.getenv("GITHUB_RUN_ATTEMPT","unknown")},
      "signing":{"kid":os.getenv("DADI_SIGNING_KID",""),"key_ref":os.getenv("AWS_KMS_KEY_ID","")},
      "artifact_digests_sha256":artifacts
    }
    (root/"PROVENANCE.json").write_text(json.dumps(prov,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("Wrote PROVENANCE.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
