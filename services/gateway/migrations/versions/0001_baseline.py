"""Baseline schema for DADI Gateway (raw SQL apply)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-02-28 02:15:36
"""

from __future__ import annotations
from alembic import op
from pathlib import Path
import json
import hashlib

def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _load_checksums(repo_root: Path) -> dict:
    p = repo_root / "services" / "gateway" / "migrations" / "checksums.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def _prod_mode() -> bool:
    return os.getenv("DADI_ENV", "dev").strip().lower() in ("prod","production")

import os

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

SQL_ORDER = [
    "schema.sql",
    "tenant_isolation_migration.sql",
    "enable_rls.sql",
    "regeneration_plans.sql",
    "deliverables.sql",
    "deliverables_record_migration.sql",
    "deliverable_bundles.sql",
    "deliverable_evidence.sql",
    "audit_events.sql",
    "audit_hash_chain.sql",
    "signing_public_keys.sql",
    "idempotency.sql",
    "revocation.sql",
]

def upgrade() -> None:
    conn = op.get_bind()
    repo_root = Path(__file__).resolve().parents[4]
    checksums = _load_checksums(repo_root)
    sql_root = repo_root / "services" / "gateway" / "sql"
    for name in SQL_ORDER:
        p = sql_root / name
        if not p.exists():
            if _prod_mode():
                raise RuntimeError(f"Missing required SQL migration file in prod: {name}")
            else:
                continue
        b = p.read_bytes()
        expected = checksums.get(name)
        if expected and _sha256_hex(b) != expected:
            raise RuntimeError(f"SQL file checksum mismatch: {name}")
        sql = b.decode('utf-8')
        if sql.strip():
            conn.execute(sql)

def downgrade() -> None:
    pass

