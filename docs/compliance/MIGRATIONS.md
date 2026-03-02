# Migration Discipline (Alembic)

Baseline revision: `0001_baseline`

Run: `make migrate`


## SQL checksum enforcement

Baseline migration validates SQL file SHA256 checksums against `services/gateway/migrations/checksums.json` in prod mode.
