from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from fastapi import Request
from .db import conn_with_tenant, tx_with_tenant

IDEMPOTENCY_HEADER = "Idempotency-Key"

def get_idempotency_key(request: Request) -> Optional[str]:
    return request.headers.get(IDEMPOTENCY_HEADER)

def lookup_response(tenant: str, key: str, method: str, path: str) -> Optional[Tuple[int, Dict[str, Any]]]:
    with conn_with_tenant(tenant) as c:
        row = c.execute(
            "SELECT response_status, response_json FROM idempotency_keys WHERE tenant_id=%s AND idempotency_key=%s AND method=%s AND path=%s",
            (tenant, key, method, path),
        ).fetchone()
    if not row:
        return None
    status, payload = row
    data = payload if isinstance(payload, dict) else json.loads(payload)
    return int(status), data

def store_response(tenant: str, key: str, method: str, path: str, status: int, payload: Dict[str, Any]) -> None:
    with tx_with_tenant(tenant) as c:
        c.execute(
            "INSERT INTO idempotency_keys (tenant_id, idempotency_key, method, path, response_status, response_json) "
            "VALUES (%s,%s,%s,%s,%s,%s::jsonb) "
            "ON CONFLICT (tenant_id, idempotency_key, method, path) DO NOTHING",
            (tenant, key, method, path, int(status), json.dumps(payload)),
        )
