-- DADI Artifact Store + Lineage Graph + Memoization Layer
-- Postgres DDL (minimal, production-credible)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS artifacts (
  sha256 CHAR(64) PRIMARY KEY,
  artifact_type TEXT NOT NULL,
  schema_version TEXT NULL,
  media_type TEXT NOT NULL,
  byte_length BIGINT NOT NULL,
  canonical BOOLEAN NOT NULL DEFAULT FALSE,
  canonical_format TEXT NULL,
  storage_backend TEXT NOT NULL DEFAULT 'postgres',
  storage_ref TEXT NULL,
  content BYTEA NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT artifacts_storage_content_chk
    CHECK (
      (storage_backend = 'postgres' AND content IS NOT NULL)
      OR
      (storage_backend = 'blob' AND content IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS artifacts_type_idx ON artifacts (artifact_type);
CREATE INDEX IF NOT EXISTS artifacts_created_idx ON artifacts (created_at);

CREATE TABLE IF NOT EXISTS pipelines (
  pipeline_id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  pipeline_run_id UUID PRIMARY KEY,
  pipeline_id UUID NOT NULL REFERENCES pipelines(pipeline_id) ON DELETE CASCADE,
  document_version_id UUID NULL,
  status TEXT NOT NULL CHECK (status IN ('running','success','failed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS stage_runs (
  stage_run_id UUID PRIMARY KEY,
  pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(pipeline_run_id) ON DELETE CASCADE,
  stage_index INT NOT NULL,
  stage_name TEXT NOT NULL,
  stage_schema_version TEXT NOT NULL,
  toolchain_manifest_sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256),
  prompt_bundle_sha256 CHAR(64) NULL REFERENCES artifacts(sha256),
  input_artifact_sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256),
  output_artifact_sha256 CHAR(64) NULL REFERENCES artifacts(sha256),
  status TEXT NOT NULL CHECK (status IN ('success','failed')),
  fail_closed BOOLEAN NOT NULL DEFAULT FALSE,
  deterministic_error_artifact_sha256 CHAR(64) NULL REFERENCES artifacts(sha256),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ NULL,
  UNIQUE (pipeline_run_id, stage_index)
);

CREATE INDEX IF NOT EXISTS stage_runs_by_input_idx ON stage_runs (stage_name, stage_schema_version, input_artifact_sha256);
CREATE INDEX IF NOT EXISTS stage_runs_by_output_idx ON stage_runs (output_artifact_sha256);

CREATE TABLE IF NOT EXISTS artifact_edges (
  edge_id BIGSERIAL PRIMARY KEY,
  from_sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256) ON DELETE CASCADE,
  to_sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256) ON DELETE CASCADE,
  edge_type TEXT NOT NULL CHECK (edge_type IN ('consumes','produces','references','base_of_delta')),
  stage_run_id UUID NULL REFERENCES stage_runs(stage_run_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS artifact_edges_from_idx ON artifact_edges (from_sha256);
CREATE INDEX IF NOT EXISTS artifact_edges_to_idx ON artifact_edges (to_sha256);
CREATE INDEX IF NOT EXISTS artifact_edges_stage_run_idx ON artifact_edges (stage_run_id);

CREATE TABLE IF NOT EXISTS stage_cache (
  cache_id BIGSERIAL PRIMARY KEY,
  stage_name TEXT NOT NULL,
  stage_schema_version TEXT NOT NULL,
  input_artifact_sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256) ON DELETE CASCADE,
  output_artifact_sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (stage_name, stage_schema_version, input_artifact_sha256)
);

CREATE INDEX IF NOT EXISTS stage_cache_lookup_idx
  ON stage_cache (stage_name, stage_schema_version, input_artifact_sha256);
