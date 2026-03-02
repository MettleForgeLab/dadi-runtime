# Example renderer usage (requires DATABASE_URL and artifacts present)

import os, json
from dadi_renderer.store import get_artifact_bytes
from dadi_renderer.stage06_handler import stage06_render_docx

if __name__ == "__main__":
    # stage_input stub with render_input sha pointer
    stage_input = {
        "schema_version": "stage_input-v1",
        "stage": {"index": 6, "name": "06_render", "schema_version": "v1"},
        "docpack_sha256": "0"*64,
        "prior_outputs": [],
        "prompt_bundle_sha256": None,
        "toolchain_manifest_sha256": "0"*64,
        "params": {
            "render_input_sha256": os.getenv("RENDER_INPUT_SHA256")
        }
    }
    out = stage06_render_docx(stage_input)
    print(json.dumps(out, indent=2))
