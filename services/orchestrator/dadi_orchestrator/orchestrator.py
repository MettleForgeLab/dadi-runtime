from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, List

from .hashing import canonical_json_bytes
from .schema_registry import SchemaRegistry, validate_or_error_artifact
from . import store_adapter as store

StageHandler = Callable[[Dict[str, Any], "StageContext"], Dict[str, Any]]

@dataclass(frozen=True)
class StageSpec:
    index: int
    name: str
    schema_version: str
    output_schema_version: str
    handler: StageHandler
    uses_prompt: bool = True

@dataclass
class StageContext:
    registry: SchemaRegistry
    schemas_path: str

    def get_artifact_bytes(self, sha256: str) -> bytes:
        b = store.get_artifact_content(sha256)
        if b is None:
            raise RuntimeError(f"Artifact content not available for sha256={sha256}")
        return b

class Orchestrator:
    def __init__(self, schemas_path: str) -> None:
        self.schemas_path = schemas_path
        self.registry = SchemaRegistry(schemas_path)

    def run(
        self,
        pipeline_run_id: str,
        docpack_sha256: str,
        toolchain_manifest_sha256: str,
        prompt_bundle_sha256: Optional[str],
        stages: List[StageSpec],
        params: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        params = params or {}
        ctx = StageContext(self.registry, self.schemas_path)

        outputs: List[str] = []
        prior_outputs: List[str] = []

        for stage in stages:
            stage_input = {
                "schema_version": "stage_input-v1",
                "stage": {"index": stage.index, "name": stage.name, "schema_version": stage.schema_version},
                "docpack_sha256": docpack_sha256,
                "prior_outputs": prior_outputs,
                "prompt_bundle_sha256": prompt_bundle_sha256 if stage.uses_prompt else None,
                "toolchain_manifest_sha256": toolchain_manifest_sha256,
                "params": params,
            }

            ok_in, _, in_or_err = validate_or_error_artifact(self.registry, stage_input)
            if not ok_in:
                err_sha = store.put_artifact(
                    artifact_type="errors/validation",
                    media_type="application/json",
                    content=canonical_json_bytes(in_or_err),
                    canonical=True,
                    canonical_format="json_c14n_v1",
                    schema_version="validation_error-v1",
                )
                raise RuntimeError(f"Stage input validation failed (fail-closed). error_sha256={err_sha}")

            stage_input_sha = store.put_artifact(
                artifact_type=f"pipeline/stage/{stage.index:02d}/input-v1",
                media_type="application/json",
                content=canonical_json_bytes(stage_input),
                canonical=True,
                canonical_format="json_c14n_v1",
                schema_version="stage_input-v1",
            )

            hit = store.cache_lookup(stage.name, stage.schema_version, stage_input_sha)
            if hit:
                outputs.append(hit)
                prior_outputs.append(hit)
                store.record_edge(stage_input_sha, hit, "produces", stage_run_id=None)
                continue

            stage_run_id = store.insert_stage_run(
                pipeline_run_id=pipeline_run_id,
                stage_index=stage.index,
                stage_name=stage.name,
                stage_schema_version=stage.schema_version,
                toolchain_manifest_sha256=toolchain_manifest_sha256,
                prompt_bundle_sha256=prompt_bundle_sha256 if stage.uses_prompt else None,
                input_artifact_sha256=stage_input_sha,
            )

            try:
                out_obj = stage.handler(stage_input, ctx)
            except Exception as e:
                err = {
                    "schema_version": "execution_error-v1",
                    "stage": {"index": stage.index, "name": stage.name, "schema_version": stage.schema_version},
                    "message": str(e),
                }
                err_sha = store.put_artifact(
                    artifact_type="errors/execution",
                    media_type="application/json",
                    content=canonical_json_bytes(err),
                    canonical=True,
                    canonical_format="json_c14n_v1",
                    schema_version="execution_error-v1",
                )
                store.finalize_stage_run_fail_closed(stage_run_id, err_sha)
                raise

            ok_out, _, out_or_err = validate_or_error_artifact(self.registry, out_obj)
            if not ok_out:
                err_sha = store.put_artifact(
                    artifact_type="errors/validation",
                    media_type="application/json",
                    content=canonical_json_bytes(out_or_err),
                    canonical=True,
                    canonical_format="json_c14n_v1",
                    schema_version="validation_error-v1",
                )
                store.finalize_stage_run_fail_closed(stage_run_id, err_sha)
                raise RuntimeError(f"Stage output validation failed (fail-closed). stage={stage.name} error_sha256={err_sha}")

            out_sha = store.put_artifact(
                artifact_type=f"pipeline/stage/{stage.index:02d}/output-v1",
                media_type="application/json",
                content=canonical_json_bytes(out_obj),
                canonical=True,
                canonical_format="json_c14n_v1",
                schema_version=out_obj.get("schema_version"),
            )

            store.record_edge(docpack_sha256, stage_input_sha, "consumes", stage_run_id=stage_run_id)
            for po in prior_outputs:
                store.record_edge(po, stage_input_sha, "consumes", stage_run_id=stage_run_id)
            store.record_edge(stage_input_sha, out_sha, "produces", stage_run_id=stage_run_id)

            store.cache_record(stage.name, stage.schema_version, stage_input_sha, out_sha)
            store.finalize_stage_run_success(stage_run_id, out_sha)

            outputs.append(out_sha)
            prior_outputs.append(out_sha)

        return outputs
