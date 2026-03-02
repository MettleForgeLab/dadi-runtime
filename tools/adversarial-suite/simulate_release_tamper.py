\
#!/usr/bin/env python3
import argparse
import json
import shutil
import tempfile
from pathlib import Path
import subprocess

def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)

def flip_one_byte(p: Path):
    b = bytearray(p.read_bytes())
    b[len(b)//2] = (b[len(b)//2] + 1) % 256
    p.write_bytes(bytes(b))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release-dir", required=True)
    args = ap.parse_args()
    src = Path(args.release_dir).resolve()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        work = td / "release"
        shutil.copytree(src, work)

        # baseline should pass
        base = sh(["python","scripts/verify_release_manifest.py"], cwd=work)
        print("baseline verify:", base.returncode)

        # flip critical file if present
        critical = work / "docs" / "compliance" / "THREAT_MODEL.md"
        if critical.exists():
            flip_one_byte(critical)
        out = sh(["python","scripts/verify_release_manifest.py"], cwd=work)
        print("after critical file tamper:", out.returncode)
        print(out.stdout[-2000:])
        print(out.stderr[-2000:])

        return 0 if out.returncode != 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
