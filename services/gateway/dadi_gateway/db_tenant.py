\
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg

def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url

@contextmanager
def tx_with_tenant(tenant_id: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(get_database_url()) as c:
        with c.transaction():
            c.execute("SET app.tenant_id = %s", (tenant_id,))
            yield c

@contextmanager
def conn_with_tenant(tenant_id: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(get_database_url()) as c:
        c.execute("SET app.tenant_id = %s", (tenant_id,))
        yield c
