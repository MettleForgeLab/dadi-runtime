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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release-dir", required=True)
    ap.add_argument("--public-keys", default="RELEASE_PUBLIC_KEYS.json")
    args = ap.parse_args()
    src = Path(args.release_dir).resolve()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        work = td / "release"
        shutil.copytree(src, work)

        pk = work / args.public_keys
        if not pk.exists():
            print("SKIP: RELEASE_PUBLIC_KEYS.json not present in this release dir")
            return 0

        # Replace keys with empty set => should fail external verifier
        pk.write_text(json.dumps({"keys":[]}, indent=2) + "\n", encoding="utf-8")
        r = sh(["python","tools/release-verifier/verify_release.py","--release-dir",".","--public-keys",args.public_keys], cwd=work)
        print("external verify exit:", r.returncode)
        return 0 if r.returncode != 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
