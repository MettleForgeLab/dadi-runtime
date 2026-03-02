from tests.test_client import session

import os
import requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000")

def test_plan_explain_shape():
    # Minimal regeneration request (likely empty unless seeded)
    req = {
        "old_prompt_sha256": "c"*64,
        "new_prompt_sha256": "d"*64
    }
    r = session().post(f"{API}/plan/regenerate", json=req)
    if r.status_code == 400:
        # acceptable if no matching stage_runs; planner still should not crash
        return
    r.raise_for_status()
    plan = r.json()
    plan_id = plan["plan_id"]

    r2 = session().get(f"{API}/plan/{plan_id}/explain")
    r2.raise_for_status()
    explain = r2.json()

    assert explain["plan_id"] == plan_id
    assert "explain_items" in explain
