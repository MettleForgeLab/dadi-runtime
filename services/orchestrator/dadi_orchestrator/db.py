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

def get_tenant_id() -> str:
    # Orchestrator must run with explicit tenant context in tenant-scoped deployments.
    tenant = os.getenv("DADI_TENANT_ID")
    if not tenant:
        raise RuntimeError("DADI_TENANT_ID is not set (required for tenant-scoped DB)")
    return tenant

@contextmanager
def tx() -> Iterator[psycopg.Connection]:
    tenant = get_tenant_id()
    with psycopg.connect(get_database_url()) as c:
        with c.transaction():
            # Required for RLS enforcement
            c.execute("SET app.tenant_id = %s", (tenant,))
            yield c

@contextmanager
def conn() -> Iterator[psycopg.Connection]:
    tenant = get_tenant_id()
    with psycopg.connect(get_database_url()) as c:
        c.execute("SET app.tenant_id = %s", (tenant,))
        yield c
