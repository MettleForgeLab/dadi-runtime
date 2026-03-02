from __future__ import annotations

import argparse
import json
import sys

from .models import RegenerateRequest
from .planner import plan_regeneration, get_plan, mark_executed

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="dadi-regen")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Create a regeneration plan")
    p_plan.add_argument("--old-prompt-sha", dest="old_prompt_sha256")
    p_plan.add_argument("--new-prompt-sha", dest="new_prompt_sha256")
    p_plan.add_argument("--old-toolchain-sha", dest="old_toolchain_sha256")
    p_plan.add_argument("--new-toolchain-sha", dest="new_toolchain_sha256")
    p_plan.add_argument("--pipeline-id", dest="pipeline_id")
    p_plan.add_argument("--created-after", dest="created_after")
    p_plan.add_argument("--created-before", dest="created_before")

    p_get = sub.add_parser("get", help="Fetch a plan")
    p_get.add_argument("--plan-id", required=True)

    p_exec = sub.add_parser("execute", help="Mark plan executed (no-op execution by default)")
    p_exec.add_argument("--plan-id", required=True)

    args = p.parse_args(argv)

    if args.cmd == "plan":
        req = RegenerateRequest(
            old_prompt_sha256=args.old_prompt_sha256,
            new_prompt_sha256=args.new_prompt_sha256,
            old_toolchain_sha256=args.old_toolchain_sha256,
            new_toolchain_sha256=args.new_toolchain_sha256,
            pipeline_id=args.pipeline_id,
            created_after=args.created_after,
            created_before=args.created_before,
        )
        plan = plan_regeneration(req)
        print(plan.model_dump_json(indent=2))
        return 0

    if args.cmd == "get":
        plan = get_plan(args.plan_id)
        print(plan.model_dump_json(indent=2))
        return 0

    if args.cmd == "execute":
        # Optional: wire to orchestrator here. Default is status update only.
        mark_executed(args.plan_id)
        print(json.dumps({"ok": True, "plan_id": args.plan_id, "status": "executed"}))
        return 0

    return 1

if __name__ == "__main__":
    raise SystemExit(main())
