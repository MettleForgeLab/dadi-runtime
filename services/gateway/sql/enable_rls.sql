-- Enable Row-Level Security for tenant-scoped tables
-- Version: v0.1

BEGIN;

-- Function safety: ensure tenant_id is set
CREATE OR REPLACE FUNCTION enforce_tenant_set()
RETURNS void AS $$
BEGIN
  IF current_setting('app.tenant_id', true) IS NULL THEN
    RAISE EXCEPTION 'app.tenant_id is not set';
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Tables to protect
DO $$
DECLARE
  t TEXT;
BEGIN
  FOR t IN SELECT unnest(ARRAY[
    'artifacts',
    'artifact_edges',
    'stage_cache',
    'pipeline_runs',
    'stage_runs',
    'regeneration_plans'
  ])
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);

    EXECUTE format($policy$
      CREATE POLICY %I_tenant_policy ON %I
      USING (tenant_id = current_setting('app.tenant_id'))
      WITH CHECK (tenant_id = current_setting('app.tenant_id'));
    $policy$, t, t);
  END LOOP;
END $$;

COMMIT;

-- IMPORTANT:
-- The application must execute:
--   SET app.tenant_id = '<tenant>';
-- at the beginning of every transaction.
