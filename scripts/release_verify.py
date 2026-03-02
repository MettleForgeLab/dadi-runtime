#!/usr/bin/env python3
import os
import subprocess
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sh(cmd, env=None):
    return subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)

def main():
    report = {"ok": False, "steps": []}

    # Presence checks
    required = [
        ROOT / "alembic.ini",
        ROOT / "services" / "gateway" / "migrations" / "env.py",
        ROOT / "docs" / "compliance" / "THREAT_MODEL.md",
        ROOT / "docs" / "compliance" / "AUTHZ_MATRIX.md",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        report["steps"].append({"step": "presence_check", "ok": False, "missing": missing})
        print(json.dumps(report, indent=2))
        return 2
    report["steps"].append({"step": "presence_check", "ok": True})

    api = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000").rstrip("/")
    idp = os.getenv("IDP_URL", "http://localhost:9000").rstrip("/")

    # Compliance gate
    g = sh(["make", "compliance-gate"], env={**os.environ, "NEXT_PUBLIC_API_BASE": api})
    report["steps"].append({"step": "compliance_gate", "exit_code": g.returncode, "stdout_tail": g.stdout[-2000:], "stderr_tail": g.stderr[-2000:]})
    if g.returncode != 0:
        print(json.dumps(report, indent=2))
        return 2

    # Compliance smoke
    s = sh(["make", "compliance-smoke"], env={**os.environ, "API_BASE": api, "IDP_URL": idp})
    report["steps"].append({"step": "compliance_smoke", "exit_code": s.returncode, "stdout_tail": s.stdout[-2000:], "stderr_tail": s.stderr[-2000:]})
    if s.returncode != 0:
        print(json.dumps(report, indent=2))
        return 2

    report["ok"] = True
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
