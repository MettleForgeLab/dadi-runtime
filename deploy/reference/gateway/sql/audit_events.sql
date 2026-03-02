-- Audit events (tenant-scoped)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS audit_events (
  tenant_id TEXT NOT NULL,
  event_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_type TEXT NOT NULL,
  pipeline_run_id UUID NULL,
  deliverable_id UUID NULL,
  bundle_id UUID NULL,
  idempotency_key TEXT NULL,
  detail_json JSONB NOT NULL,
  prev_event_hash CHAR(64) NULL,
  event_hash CHAR(64) NULL,
  PRIMARY KEY (tenant_id, event_id)
);

CREATE INDEX IF NOT EXISTS audit_events_created_idx ON audit_events (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_run_idx ON audit_events (tenant_id, pipeline_run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_deliverable_idx ON audit_events (tenant_id, deliverable_id, created_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_hash_idx ON audit_events (tenant_id, event_hash);
