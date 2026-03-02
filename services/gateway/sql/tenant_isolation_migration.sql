-- Tenant isolation migration (best-effort) for existing DADI schema
-- WARNING: This alters primary keys and foreign keys. Apply in a maintenance window.
-- Version: v0.1

BEGIN;

-- 1) Add tenant_id columns (default to 'default' for existing rows)
ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE artifact_edges ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE stage_cache ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE stage_runs ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE regeneration_plans ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';

-- 2) Drop dependent foreign keys that reference artifacts(sha256)
-- (names may vary if schema was created differently; adjust if needed)
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT conname, conrelid::regclass::text AS tbl
    FROM pg_constraint
    WHERE confrelid = 'artifacts'::regclass
  LOOP
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', r.tbl, r.conname);
  END LOOP;
END $$;

-- 3) Replace artifacts primary key with (tenant_id, sha256)
-- Drop existing PK if present
DO $$
DECLARE
  pkname text;
BEGIN
  SELECT conname INTO pkname
  FROM pg_constraint
  WHERE conrelid = 'artifacts'::regclass AND contype = 'p';
  IF pkname IS NOT NULL THEN
    EXECUTE format('ALTER TABLE artifacts DROP CONSTRAINT %I', pkname);
  END IF;
END $$;

ALTER TABLE artifacts ADD CONSTRAINT artifacts_pkey PRIMARY KEY (tenant_id, sha256);

-- 4) Recreate foreign keys with tenant_id
-- Add sha256 columns in dependent tables already exist; we add tenant_id alignment by composite references.

-- stage_runs references artifacts
ALTER TABLE stage_runs
  ADD CONSTRAINT stage_runs_toolchain_fk FOREIGN KEY (tenant_id, toolchain_manifest_sha256) REFERENCES artifacts(tenant_id, sha256),
  ADD CONSTRAINT stage_runs_prompt_fk FOREIGN KEY (tenant_id, prompt_bundle_sha256) REFERENCES artifacts(tenant_id, sha256),
  ADD CONSTRAINT stage_runs_input_fk FOREIGN KEY (tenant_id, input_artifact_sha256) REFERENCES artifacts(tenant_id, sha256),
  ADD CONSTRAINT stage_runs_output_fk FOREIGN KEY (tenant_id, output_artifact_sha256) REFERENCES artifacts(tenant_id, sha256),
  ADD CONSTRAINT stage_runs_error_fk FOREIGN KEY (tenant_id, deterministic_error_artifact_sha256) REFERENCES artifacts(tenant_id, sha256);

-- stage_cache references artifacts
ALTER TABLE stage_cache
  ADD CONSTRAINT stage_cache_input_fk FOREIGN KEY (tenant_id, input_artifact_sha256) REFERENCES artifacts(tenant_id, sha256) ON DELETE CASCADE,
  ADD CONSTRAINT stage_cache_output_fk FOREIGN KEY (tenant_id, output_artifact_sha256) REFERENCES artifacts(tenant_id, sha256) ON DELETE CASCADE;

-- artifact_edges references artifacts
ALTER TABLE artifact_edges
  ADD CONSTRAINT artifact_edges_from_fk FOREIGN KEY (tenant_id, from_sha256) REFERENCES artifacts(tenant_id, sha256) ON DELETE CASCADE,
  ADD CONSTRAINT artifact_edges_to_fk FOREIGN KEY (tenant_id, to_sha256) REFERENCES artifacts(tenant_id, sha256) ON DELETE CASCADE;

-- 5) Update unique constraints to include tenant_id
-- stage_cache uniqueness
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conrelid='stage_cache'::regclass AND contype='u'
  ) THEN
    -- leave existing; manual adjustment may be required depending on name
    NULL;
  END IF;
END $$;

ALTER TABLE stage_cache DROP CONSTRAINT IF EXISTS stage_cache_stage_name_stage_schema_version_input_artifact_sha256_key;
ALTER TABLE stage_cache ADD CONSTRAINT stage_cache_unique UNIQUE (tenant_id, stage_name, stage_schema_version, input_artifact_sha256);

-- stage_runs unique per pipeline_run_id, stage_index, tenant
ALTER TABLE stage_runs DROP CONSTRAINT IF EXISTS stage_runs_pipeline_run_id_stage_index_key;
ALTER TABLE stage_runs ADD CONSTRAINT stage_runs_unique UNIQUE (tenant_id, pipeline_run_id, stage_index);

-- 6) Indexes (tenant-aware)
CREATE INDEX IF NOT EXISTS artifacts_tenant_idx ON artifacts (tenant_id);
CREATE INDEX IF NOT EXISTS artifact_edges_tenant_from_idx ON artifact_edges (tenant_id, from_sha256);
CREATE INDEX IF NOT EXISTS artifact_edges_tenant_to_idx ON artifact_edges (tenant_id, to_sha256);
CREATE INDEX IF NOT EXISTS stage_cache_tenant_lookup_idx ON stage_cache (tenant_id, stage_name, stage_schema_version, input_artifact_sha256);
CREATE INDEX IF NOT EXISTS stage_runs_tenant_idx ON stage_runs (tenant_id, pipeline_run_id);

COMMIT;

-- After migration, set application layer to require tenant_id and always filter by it.
