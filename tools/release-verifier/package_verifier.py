#!/usr/bin/env python3
import zipfile
from pathlib import Path

FILES = [
    "audit_verify.py",
    "verify_release.py",
    "requirements.txt",
    "requirements.lock.txt",
    "release_public_keys.example.json",
    "README.md",
    "run.sh",
    "run.ps1",
    "EXTERNAL_AUDIT.md",
]

def main():
    root = Path(__file__).resolve().parent
    out = root / "release-verifier.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            p = root / name
            if p.exists():
                z.write(p, arcname=name)
    print("Wrote", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
