from __future__ import annotations
from typing import Dict, Any
from dadi_orchestrator.orchestrator import StageContext

def stage02_classify(stage_input: Dict[str, Any], ctx: StageContext) -> Dict[str, Any]:
    return {
        "schema_version": "stage02-output-v1",
        "stage": {"index": 2, "name": "02_classify", "schema_version": "v1"},
        "results": {
            "doc_profile": {"doc_types": ["unknown"], "confidence": 0.0},
            "section_map": [],
            "content_index": {"tables": [], "figures": [], "key_blocks": []},
            "extraction_plan": {"targets": ["unknown"], "priority": [{"target": "unknown", "importance": "low"}]}
        },
        "citations": [],
        "provenance": {"input_sha256": "0"*64, "prompt_bundle_sha256": "1"*64}
    }
