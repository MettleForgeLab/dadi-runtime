import os, base64, json, requests

API = os.getenv("DADI_STORE_URL", "http://localhost:8000")

def put_json(artifact_type: str, obj: dict, schema_version: str):
    b = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload = {
        "meta": {
            "artifact_type": artifact_type,
            "media_type": "application/json",
            "canonical": True,
            "canonical_format": "json_c14n_v1",
            "schema_version": schema_version
        },
        "content_b64": base64.b64encode(b).decode("ascii")
    }
    r = requests.post(f"{API}/artifacts", json=payload)
    r.raise_for_status()
    return r.json()["sha256"]

if __name__ == "__main__":
    sha = put_json("doc/normalized/docpack-v1", {"schema_version":"docpack-v1","raw_sha256":"0"*64,"pages":[{"page_num":1,"blocks":[{"block_id":"b1","type":"text","text":"Hello"}]}]}, "docpack-v1")
    print("stored docpack sha256:", sha)
