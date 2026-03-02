from __future__ import annotations

import os
from alembic import context
from sqlalchemy import create_engine, pool

# Alembic Config object, provides access to values in alembic.ini
config = context.config

# Optional: if alembic.ini has sqlalchemy.url, this reads it.
# We'll prefer DATABASE_URL if set.
def get_db_url() -> str:
    return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

target_metadata = None  # no ORM metadata; migrations are SQL-only

def run_migrations_offline() -> None:
    url = get_db_url()
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    url = get_db_url()
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, transactional_ddl=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()