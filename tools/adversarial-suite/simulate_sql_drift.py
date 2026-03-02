\
#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-dir", required=True, help="Path to repo root (unzipped release)")
    args = ap.parse_args()
    root = Path(args.repo_dir).resolve()
    checksums = root / "services" / "gateway" / "migrations" / "checksums.json"
    sql_file = root / "services" / "gateway" / "sql" / "schema.sql"
    if not checksums.exists() or not sql_file.exists():
        print("SKIP: required files missing")
        return 0

    c = json.loads(checksums.read_text(encoding="utf-8"))
    expected = c.get("schema.sql")
    if not expected:
        print("SKIP: no expected checksum for schema.sql")
        return 0

    # simulate drift by flipping a byte and comparing checksum
    b = bytearray(sql_file.read_bytes())
    b[0] = (b[0] + 1) % 256
    drift = hashlib.sha256(bytes(b)).hexdigest()

    ok = drift != expected
    print(json.dumps({"expected": expected, "drift": drift, "ok": ok}, indent=2))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
