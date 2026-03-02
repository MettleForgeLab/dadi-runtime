-- Optional LLM call ledger (links request/response artifacts to stage_runs)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS llm_calls (
  llm_call_id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  stage_run_id UUID NULL REFERENCES stage_runs(stage_run_id) ON DELETE SET NULL,
  request_artifact_sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256) ON DELETE CASCADE,
  response_artifact_sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('live','replay','drift'))
);

CREATE INDEX IF NOT EXISTS llm_calls_stage_run_idx ON llm_calls (stage_run_id);
CREATE INDEX IF NOT EXISTS llm_calls_request_idx ON llm_calls (request_artifact_sha256);
