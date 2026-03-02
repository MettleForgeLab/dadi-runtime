-- Revocation support for bundles and evidence
-- Version: v0.1

ALTER TABLE deliverable_bundles
  ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ NULL;

ALTER TABLE deliverable_evidence
  ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ NULL;
