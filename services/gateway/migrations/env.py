from __future__ import annotations
import os
from alembic import context

def get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url

def run_migrations_online() -> None:
    import psycopg
    conn = psycopg.connect(get_url())
    try:
        with conn:
            context.configure(connection=conn, transactional_ddl=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        conn.close()

run_migrations_online()
