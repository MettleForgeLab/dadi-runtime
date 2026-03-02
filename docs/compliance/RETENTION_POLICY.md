# Retention and Revocation Policy

Artifacts are immutable. Retention and revocation are implemented at the record layer:

- `deliverable_bundles` can be revoked (`status='revoked'`).
- `deliverable_evidence` can be revoked (`status='revoked'`).

Download endpoints refuse revoked objects (409).

## Retention sweep

A best-effort sweep script is provided:

- `scripts/retention_sweep.py`

Env:
- `DADI_BUNDLE_RETENTION_DAYS` (default 30)
- `DADI_EVIDENCE_RETENTION_DAYS` (default 90)

The sweep marks records as revoked. It does not delete artifact bytes by default.
Byte deletion should be a separate policy decision.
