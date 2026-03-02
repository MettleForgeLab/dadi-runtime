"""Baseline schema for DADI Gateway (raw SQL apply)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-02-28 02:15:36
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from alembic import op
from sqlalchemy import text

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


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _prod_mode() -> bool:
    return os.getenv("DADI_ENV", "dev").strip().lower() in ("prod", "production")


def _find_repo_root(p: Path) -> Path:
    """
    Works for both:
      - canonical: .../services/gateway/migrations/versions/0001_baseline.py
      - reference: /app/migrations/versions/0001_baseline.py
    """
    markers = {"pyproject.toml", "README.md", "alembic.ini"}
    for parent in p.parents:
        if any((parent / m).exists() for m in markers):
            return parent
    return p.parents[-1]


def _load_checksums(repo_root: Path) -> dict[str, str]:
    """
    checksums.json may exist in canonical repo. If absent, proceed without checksums.
    """
    candidates = [
        repo_root / "services" / "gateway" / "migrations" / "checksums.json",
        repo_root / "migrations" / "checksums.json",
    ]
    for c in candidates:
        if c.exists():
            return json.loads(c.read_text(encoding="utf-8"))
    return {}


def _resolve_sql_root(repo_root: Path) -> Path:
    """
    Prefer the reference image location first (/app/sql), then fall back to canonical layout.
    """
    # In the reference gateway container, SQL is copied to /app/sql
    ref_sql = Path("/app/sql")
    if ref_sql.exists():
        return ref_sql

    # In canonical layout, SQL lives under services/gateway/sql
    canon_sql = repo_root / "services" / "gateway" / "sql"
    if canon_sql.exists():
        return canon_sql

    # Last resort: sibling sql directory (unlikely)
    fallback = repo_root / "sql"
    return fallback


def upgrade() -> None:
    conn = op.get_bind()

    here = Path(__file__).resolve()
    repo_root = _find_repo_root(here)
    sql_root = _resolve_sql_root(repo_root)
    checksums = _load_checksums(repo_root)

    for name in SQL_ORDER:
        sql_path = sql_root / name
        if not sql_path.exists():
            if _prod_mode():
                raise RuntimeError(f"Missing required SQL migration file in prod: {sql_path}")
            # dev mode: skip missing optional files
            continue

        b = sql_path.read_bytes()

        expected = checksums.get(name)
        if expected and _sha256_hex(b) != expected:
            raise RuntimeError(f"SQL file checksum mismatch: {name}")

        sql = b.decode("utf-8")
        if sql.strip():
            # Use SQLAlchemy-safe execution for raw SQL strings
            conn.execute(text(sql))


def downgrade() -> None:
    pass