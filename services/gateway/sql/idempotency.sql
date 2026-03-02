-- Idempotency support (tenant-scoped)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS idempotency_keys (
  tenant_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  response_status INT NOT NULL,
  response_json JSONB NOT NULL,
  PRIMARY KEY (tenant_id, idempotency_key, method, path)
);

CREATE INDEX IF NOT EXISTS idempotency_keys_created_idx ON idempotency_keys (created_at);

-- Optional: make bundle creation idempotent by manifest hash per deliverable.
-- If two bundle creations produce the same manifest_artifact_sha256, treat as same logical bundle.
DO $$
BEGIN
  BEGIN
    ALTER TABLE deliverable_bundles
      ADD CONSTRAINT deliverable_bundles_unique_manifest UNIQUE (tenant_id, deliverable_id, manifest_artifact_sha256);
  EXCEPTION WHEN others THEN
    NULL;
  END;
END $$;
