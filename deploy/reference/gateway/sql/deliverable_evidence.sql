-- Evidence packets (tenant-scoped)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS deliverable_evidence (
  tenant_id TEXT NOT NULL,
  evidence_id UUID NOT NULL,
  deliverable_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  evidence_manifest_sha256 CHAR(64) NOT NULL,
  evidence_bundle_sha256 CHAR(64) NOT NULL,
  status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created','revoked')),
  PRIMARY KEY (tenant_id, evidence_id),
  CONSTRAINT deliverable_evidence_deliverable_fk FOREIGN KEY (tenant_id, deliverable_id)
    REFERENCES deliverables(tenant_id, deliverable_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS deliverable_evidence_by_deliverable_idx ON deliverable_evidence (tenant_id, deliverable_id, created_at DESC);
