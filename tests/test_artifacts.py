from tests.test_client import session

import os
import base64
import json
import requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000")

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def test_artifact_immutability():
    obj = {"schema_version": "docpack-v1", "raw_sha256": "0"*64, "pages": [{"page_num":1,"blocks":[{"block_id":"b1","type":"text","text":"X"}]}]}
    content = canonical(obj)
    payload = {
        "meta": {
            "artifact_type": "doc/normalized/docpack-v1",
            "media_type": "application/json",
            "canonical": True,
            "canonical_format": "json_c14n_v1",
            "schema_version": "docpack-v1"
        },
        "content_b64": base64.b64encode(content).decode("ascii")
    }

    r1 = session().post(f"{API}/artifacts", json=payload)
    r1.raise_for_status()
    sha1 = r1.json()["sha256"]

    r2 = session().post(f"{API}/artifacts", json=payload)
    r2.raise_for_status()
    sha2 = r2.json()["sha256"]

    assert sha1 == sha2
