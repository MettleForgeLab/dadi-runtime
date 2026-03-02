-- Signing public keys ledger (system table; tenant-agnostic by design)
-- Version: v0.1

CREATE TABLE IF NOT EXISTS signing_public_keys (
  kid TEXT NOT NULL,
  key_ref TEXT NOT NULL,
  alg TEXT NOT NULL,
  public_key_der BYTEA NOT NULL,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (kid, key_ref, alg)
);

CREATE INDEX IF NOT EXISTS signing_public_keys_active_idx ON signing_public_keys (active, last_seen_at DESC);
