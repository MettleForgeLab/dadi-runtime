-- Deliverable record artifact pointer
-- Version: v0.2

ALTER TABLE deliverables
  ADD COLUMN IF NOT EXISTS deliverable_record_sha256 CHAR(64) NULL;

-- Best-effort FK (tenant+sha) if artifacts uses composite PK. If your schema is tenant-scoped artifacts, use composite FK.
-- If not, adjust accordingly.
DO $$
BEGIN
  -- Try composite FK (tenant_id, sha256) -> artifacts(tenant_id, sha256)
  BEGIN
    ALTER TABLE deliverables
      ADD CONSTRAINT deliverables_record_fk FOREIGN KEY (tenant_id, deliverable_record_sha256)
      REFERENCES artifacts(tenant_id, sha256);
  EXCEPTION WHEN others THEN
    -- Ignore if constraint cannot be created due to schema differences.
    NULL;
  END;
END $$;
