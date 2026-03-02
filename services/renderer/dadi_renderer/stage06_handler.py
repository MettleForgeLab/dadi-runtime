from __future__ import annotations

import json
from typing import Any, Dict

from .store import get_artifact_bytes, put_artifact_bytes
from .render_docx import render_report_model_to_docx_bytes

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

def stage06_render_docx(stage_input: Dict[str, Any], ctx=None) -> Dict[str, Any]:
    """Orchestrator-compatible stage handler for deterministic DOCX rendering.

    Expects stage_input.params to include a render_input object OR stage_input.prior_outputs to include a render_input artifact hash.
    Recommended: pass render_input-v1 as an upstream artifact and include its sha256 in prior_outputs.

    For simplicity, this handler expects params.render_input_sha256.
    """
    params = stage_input.get("params", {}) or {}
    render_input_sha = params.get("render_input_sha256")
    if not render_input_sha:
        raise ValueError("Missing params.render_input_sha256")

    render_input_bytes = get_artifact_bytes(render_input_sha)
    render_input = json.loads(render_input_bytes.decode("utf-8"))

    if render_input.get("schema_version") != "render_input-v1":
        raise ValueError("render_input artifact is not render_input-v1")

    if render_input.get("render_params", {}).get("format") != "docx":
        raise ValueError("render_input.render_params.format must be 'docx'")

    report_model_sha = render_input["report_model_sha256"]
    template_sha = render_input["template_sha256"]

    report_bytes = get_artifact_bytes(report_model_sha)
    report_model = json.loads(report_bytes.decode("utf-8"))
    if report_model.get("schema_version") != "report_model-v1":
        raise ValueError("report model artifact is not report_model-v1")

    template_bytes = get_artifact_bytes(template_sha)

    docx_bytes = render_report_model_to_docx_bytes(report_model, template_bytes=template_bytes)

    out_sha = put_artifact_bytes(
        artifact_type="report/render/docx-v1",
        media_type=DOCX_MEDIA_TYPE,
        content=docx_bytes,
        canonical=False,
        canonical_format=None,
        schema_version=None,
    )

    # Return a small JSON output (optional) that can be schema'd later; for now, return pointer dict.
    return {
        "schema_version": "render_docx_output-v1",
        "stage": {"index": 6, "name": "06_render", "schema_version": "v1"},
        "results": {
            "docx_sha256": out_sha,
            "media_type": DOCX_MEDIA_TYPE
        },
        "citations": [],
        "provenance": {
            "input_sha256": render_input_sha,
            "prompt_bundle_sha256": stage_input.get("prompt_bundle_sha256") or "0"*64
        }
    }
