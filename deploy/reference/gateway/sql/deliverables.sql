-- Deliverables layer (tenant-scoped)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS deliverables (
  tenant_id TEXT NOT NULL,
  deliverable_id UUID NOT NULL,
  pipeline_run_id UUID NOT NULL,
  stage06_output_sha256 CHAR(64) NULL,
  docx_sha256 CHAR(64) NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','final','sent','superseded')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  supersedes_deliverable_id UUID NULL,
  PRIMARY KEY (tenant_id, deliverable_id),
  CONSTRAINT deliverables_run_fk FOREIGN KEY (tenant_id, pipeline_run_id)
    REFERENCES pipeline_runs(tenant_id, pipeline_run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS deliverables_run_idx ON deliverables (tenant_id, pipeline_run_id);
CREATE INDEX IF NOT EXISTS deliverables_status_idx ON deliverables (tenant_id, status);
