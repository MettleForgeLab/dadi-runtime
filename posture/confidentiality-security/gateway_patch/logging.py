from __future__ import annotations

import os
import json
import uuid
from typing import Dict, Any, List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

def _redact_headers(headers: Dict[str, str], redact_keys: List[str]) -> Dict[str, str]:
    rk = set(k.lower() for k in redact_keys)
    out = {}
    for k, v in headers.items():
        if k.lower() in rk:
            out[k] = "[REDACTED]"
        else:
            out[k] = v
    return out

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request logging without content leakage.

    By default:
      - does not log request bodies
      - does not log response bodies
      - redacts Authorization/Cookie
    """

    def __init__(self, app, redact_headers: List[str] | None = None):
        super().__init__(app)
        self.redact_headers = redact_headers or ["authorization", "cookie"]

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request line + headers only (redacted)
        hdrs = {k: v for k, v in request.headers.items()}
        hdrs = _redact_headers(hdrs, self.redact_headers)

        log = {
            "event": "request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) if request.url.query else "",
            "headers": hdrs,
        }
        print(json.dumps(log, ensure_ascii=False))

        resp = await call_next(request)

        log2 = {
            "event": "response",
            "request_id": request_id,
            "status_code": resp.status_code,
        }
        print(json.dumps(log2, ensure_ascii=False))

        resp.headers["X-Request-Id"] = request_id
        return resp
