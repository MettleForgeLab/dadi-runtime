#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

def sh(cmd):
    return subprocess.run(cmd, check=False, capture_output=True, text=True)

def read_requirements(path: Path):
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]

def parse_pinned(line: str):
    if "==" in line:
        n,v = line.split("==",1)
        return {"name": n.strip(), "version": v.strip()}
    return {"name": line.strip(), "version": None}

def main():
    root = Path(__file__).resolve().parents[1]
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    deps=[]
    deps += [parse_pinned(l) for l in read_requirements(root/"services"/"gateway"/"requirements.txt")]
    deps += [parse_pinned(l) for l in read_requirements(root/"tools"/"release-verifier"/"requirements.txt")]
    if not deps:
        r=sh(["python","-m","pip","freeze"])
        if r.returncode==0:
            deps=[parse_pinned(l) for l in r.stdout.splitlines() if l.strip()]
    cdx={
      "bomFormat":"CycloneDX","specVersion":"1.5","version":1,
      "metadata":{"timestamp":created,"component":{"type":"application","name":"dadi-release","version":(root/"VERSION").read_text().strip() if (root/"VERSION").exists() else "unknown"}},
      "components":[{"type":"library","name":d["name"],"version":d["version"]} for d in deps if d.get("name")]
    }
    spdx={
      "spdxVersion":"SPDX-2.3","dataLicense":"CC0-1.0","SPDXID":"SPDXRef-DOCUMENT","name":"dadi-release",
      "documentNamespace":"https://mettleforgelab.example/spdx/dadi-release/"+((root/"VERSION").read_text().strip().replace(" ","_") if (root/"VERSION").exists() else "unknown"),
      "creationInfo":{"created":created,"creators":["Tool: generate_sbom.py"]},
      "packages":[{"SPDXID":f"SPDXRef-Package-{i+1}","name":d["name"],"versionInfo":d["version"] or "","downloadLocation":"NOASSERTION","licenseConcluded":"NOASSERTION"} for i,d in enumerate(deps) if d.get("name")]
    }
    (root/"SBOM.cdx.json").write_text(json.dumps(cdx,indent=2)+"\n",encoding="utf-8")
    (root/"SBOM.spdx.json").write_text(json.dumps(spdx,indent=2)+"\n",encoding="utf-8")
    print("Wrote SBOM.cdx.json and SBOM.spdx.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
