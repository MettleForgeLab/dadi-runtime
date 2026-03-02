-- Deliverable Bundles + Signed Manifests (tenant-scoped)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS deliverable_bundles (
  tenant_id TEXT NOT NULL,
  deliverable_id UUID NOT NULL,
  bundle_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  manifest_artifact_sha256 CHAR(64) NOT NULL,
  bundle_artifact_sha256 CHAR(64) NOT NULL,
  status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created','revoked')),
  PRIMARY KEY (tenant_id, bundle_id),
  CONSTRAINT deliverable_bundles_deliverable_fk FOREIGN KEY (tenant_id, deliverable_id)
    REFERENCES deliverables(tenant_id, deliverable_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS deliverable_bundles_by_deliverable_idx ON deliverable_bundles (tenant_id, deliverable_id, created_at DESC);
