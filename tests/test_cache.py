from tests.test_client import session

import os
import requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000")

def test_cache_roundtrip():
    stage_name = "demo_stage"
    schema_version = "v1"
    input_sha = "a"*64
    output_sha = "b"*64

    r = session().post(f"{API}/cache/record", json={
        "stage_name": stage_name,
        "stage_schema_version": schema_version,
        "input_sha256": input_sha,
        "output_sha256": output_sha
    })
    r.raise_for_status()

    r2 = session().get(f"{API}/cache/lookup", params={
        "stage_name": stage_name,
        "stage_schema_version": schema_version,
        "input_sha256": input_sha
    })
    r2.raise_for_status()
    data = r2.json()
    assert data["hit"] is True
    assert data["output_sha256"] == output_sha
