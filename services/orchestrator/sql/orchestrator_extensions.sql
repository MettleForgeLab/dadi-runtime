-- DADI Orchestrator extensions (optional)
-- Version: v0.1

CREATE INDEX IF NOT EXISTS stage_cache_fast_idx
  ON stage_cache (stage_name, stage_schema_version, input_artifact_sha256);

CREATE INDEX IF NOT EXISTS artifact_edges_stage_run_idx ON artifact_edges (stage_run_id);
