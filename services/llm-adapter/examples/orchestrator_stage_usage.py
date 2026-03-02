# Example: using LLMAdapter inside an orchestrator stage handler

from dadi_llm_adapter import LLMAdapter, LLMRequestV1
from examples.stub_provider import StubProvider

def stage03_extract(stage_input: dict, ctx):
    adapter = LLMAdapter(provider=StubProvider(), provider_name="stub")

    req = LLMRequestV1(
        provider="stub",
        model="stub-1",
        prompt_bundle_sha256=stage_input["prompt_bundle_sha256"],
        toolchain_manifest_sha256=stage_input["toolchain_manifest_sha256"],
        input_hashes=[stage_input["docpack_sha256"]] + stage_input["prior_outputs"],
        decoding={"temperature": 0, "top_p": 1}
    )

    req_sha, resp_sha, drift_sha = adapter.run(req, mode="live")
    body = adapter.load_response_body(resp_sha)

    # Convert body into your canonical stage output JSON...
    return {
        "schema_version": "stage03-output-v1",
        "stage": {"index": 3, "name": "03_extract", "schema_version": "v1"},
        "results": {"facts": [], "tables_normalized": [], "open_items": []},
        "citations": [],
        "provenance": {"input_sha256": "0"*64, "prompt_bundle_sha256": stage_input["prompt_bundle_sha256"]}
    }
