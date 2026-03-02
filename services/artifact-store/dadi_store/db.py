from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg

def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url

@contextmanager
def conn() -> Iterator[psycopg.Connection]:
    with psycopg.connect(get_database_url()) as c:
        yield c

@contextmanager
def tx() -> Iterator[psycopg.Connection]:
    with psycopg.connect(get_database_url()) as c:
        with c.transaction():
            yield c
