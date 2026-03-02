-- Regeneration plan storage (minimal)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS regeneration_plans (
  plan_id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','executed','cancelled')),
  request_json JSONB NOT NULL,
  plan_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS regeneration_plans_created_idx ON regeneration_plans (created_at);
