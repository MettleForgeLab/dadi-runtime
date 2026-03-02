import os
from dadi_orchestrator import Orchestrator, StageSpec
from examples.handlers import stage02_classify

if __name__ == "__main__":
    DOC_SHA = os.getenv("DOCPACK_SHA256", "0"*64)
    TOOLCHAIN_SHA = os.getenv("TOOLCHAIN_SHA256", "2"*64)
    PROMPT_SHA = os.getenv("PROMPT_SHA256", "1"*64)
    PIPELINE_RUN_ID = os.getenv("PIPELINE_RUN_ID", "00000000-0000-0000-0000-000000000000")

    orch = Orchestrator(schemas_path=os.path.join(os.path.dirname(__file__), "..", "schemas"))

    stages = [
        StageSpec(index=2, name="02_classify", schema_version="v1", output_schema_version="stage02-output-v1", handler=stage02_classify, uses_prompt=True)
    ]

    out = orch.run(
        pipeline_run_id=PIPELINE_RUN_ID,
        docpack_sha256=DOC_SHA,
        toolchain_manifest_sha256=TOOLCHAIN_SHA,
        prompt_bundle_sha256=PROMPT_SHA,
        stages=stages,
        params={}
    )
    print("outputs:", out)
