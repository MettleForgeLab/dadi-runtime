-- Regeneration plan storage (tenant-scoped)
-- Version: v0.2

CREATE TABLE IF NOT EXISTS regeneration_plans (
  tenant_id TEXT NOT NULL DEFAULT 'default',
  plan_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','executed','cancelled')),
  request_json JSONB NOT NULL,
  plan_json JSONB NOT NULL,
  PRIMARY KEY (tenant_id, plan_id)
);

CREATE INDEX IF NOT EXISTS regeneration_plans_created_idx ON regeneration_plans (created_at);
CREATE INDEX IF NOT EXISTS regeneration_plans_tenant_idx ON regeneration_plans (tenant_id);
