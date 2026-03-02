from __future__ import annotations
import os
EXPECTED_REVISION = "0001_baseline"

def schema_startup_check() -> None:
    if os.getenv("DADI_SKIP_SCHEMA_CHECK", "false").strip().lower() in ("1","true","yes"):
        return
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    import psycopg
    with psycopg.connect(url) as c:
        with c.cursor() as cur:
            cur.execute("SELECT to_regclass('public.alembic_version')")
            if cur.fetchone()[0] is None:
                raise RuntimeError("alembic_version table missing; run alembic upgrade head")
            cur.execute("SELECT version_num FROM alembic_version")
            row = cur.fetchone()
            got = row[0] if row else None
            if got != EXPECTED_REVISION:
                raise RuntimeError(f"DB schema not at expected revision: got={got} expected={EXPECTED_REVISION}")

