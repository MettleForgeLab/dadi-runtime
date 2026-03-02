from __future__ import annotations

import argparse
import json
import os
import sys

from .record import record_fixture
from .fixture import write_fixture
from .verify import verify_fixture
from .diff import diff_fixtures

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="dadi-regress")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("record", help="Record a fixture from a pipeline_run_id")
    p_rec.add_argument("--pipeline-run-id", required=True)
    p_rec.add_argument("--out", required=True, help="Output path (.zip or directory)")

    p_ver = sub.add_parser("verify", help="Verify a fixture (hashes + optional schema validation)")
    p_ver.add_argument("--fixture", required=True)
    p_ver.add_argument("--schemas", required=False, help="Path to schemas/ with index.json for JSON schema validation")

    p_diff = sub.add_parser("diff", help="Diff two fixtures (manifest-level)")
    p_diff.add_argument("--a", required=True)
    p_diff.add_argument("--b", required=True)

    args = p.parse_args(argv)

    if args.cmd == "record":
        manifest, artifacts = record_fixture(args.pipeline_run_id)
        out = write_fixture(args.out, manifest, artifacts)
        print(json.dumps({"ok": True, "out": out, "artifact_count": len(artifacts)}))
        return 0

    if args.cmd == "verify":
        res = verify_fixture(args.fixture, schemas_path=args.schemas)
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 2

    if args.cmd == "diff":
        res = diff_fixtures(args.a, args.b)
        print(json.dumps(res, indent=2))
        return 0

    return 1

if __name__ == "__main__":
    raise SystemExit(main())
