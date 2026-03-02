from __future__ import annotations

import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Fail-closed request size limits based on Content-Length.

    This protects POST /artifacts and other write endpoints from oversized payloads.

    Env:
      - DADI_MAX_REQUEST_BYTES (default 5MB)
      - DADI_MAX_ARTIFACT_UPLOAD_BYTES (default 10MB) for POST /artifacts specifically
    """

    def __init__(self, app):
        super().__init__(app)
        self.max_request = int(os.getenv("DADI_MAX_REQUEST_BYTES", str(5 * 1024 * 1024)))
        self.max_artifact_upload = int(os.getenv("DADI_MAX_ARTIFACT_UPLOAD_BYTES", str(10 * 1024 * 1024)))

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                n = int(cl)
            except Exception:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)

            limit = self.max_request
            if request.method == "POST" and request.url.path == "/artifacts":
                limit = self.max_artifact_upload

            if n > limit:
                return JSONResponse({"detail": "Request Entity Too Large", "limit_bytes": limit}, status_code=413)

        return await call_next(request)
