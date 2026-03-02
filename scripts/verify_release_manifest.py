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

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    mpath = root / "RELEASE_MANIFEST.json"
    if not mpath.exists():
        print("FAIL: RELEASE_MANIFEST.json missing")
        return 2
    m = json.loads(mpath.read_text(encoding="utf-8"))

    hashes = m.get("critical_file_hashes") or {}
    missing = []
    mismatched = []

    for rel, expected in hashes.items():
        p = root / rel
        if not p.exists():
            missing.append(rel)
            continue
        got = sha256_file(p)
        if got != expected:
            mismatched.append({"path": rel, "expected": expected, "got": got})

    items = [f"{hashes[k]}  {k}" for k in sorted(hashes.keys())]
    tree = hashlib.sha256(("\n".join(items) + "\n").encode("utf-8")).hexdigest()
    tree_ok = tree == m.get("tree_sha256")

    ok = (len(missing) == 0 and len(mismatched) == 0 and tree_ok)

    out = {
        "ok": ok,
        "missing_files": missing,
        "mismatched_files": mismatched,
        "tree_sha256_expected": m.get("tree_sha256"),
        "tree_sha256_got": tree,
    }
    print(json.dumps(out, indent=2))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
