"""Drop-in example: hardened gateway app wrapper.

This file shows how to integrate:
- BearerAuthMiddleware (auth boundary)
- StructuredLoggingMiddleware (no content logs)
- Policy gating for content endpoints

You will adapt this pattern inside your gateway's app.py.
"""

from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException, Request, Response
from dadi_gateway.app import app as base_app  # assumes your gateway app is importable as dadi_gateway.app:app
from .auth import load_policy, BearerAuthMiddleware, allow_content
from .logging import StructuredLoggingMiddleware

policy_path = os.getenv("DADI_POLICY_PATH")
policy = load_policy(policy_path) if policy_path else None

app = FastAPI(title="DADI Gateway (Hardened)", version="0.1.0")

# Middleware order: logging first, then auth (auth errors still logged without bodies)
app.add_middleware(StructuredLoggingMiddleware)
if policy:
    app.add_middleware(BearerAuthMiddleware, policy=policy)
else:
    app.add_middleware(BearerAuthMiddleware)

# Mount the base app routes under root
app.mount("", base_app)

# Example: wrap the content endpoint via an additional route that checks policy + explicit header.
# Preferred approach: modify the existing /artifacts/{sha}/content handler in your gateway to enforce this check.
# This wrapper is illustrative only.
@app.get("/_hardened/content/{sha256}")
def hardened_content(sha256: str, request: Request):
    if not policy:
        raise HTTPException(status_code=500, detail="Policy not loaded")
    if policy.content_require_auth and os.getenv("DADI_AUTH_MODE","off").lower() != "bearer":
        raise HTTPException(status_code=403, detail="Content access requires auth mode bearer")
    if not allow_content(policy, request):
        raise HTTPException(status_code=403, detail="Content access denied by policy")
    # Delegate to underlying content endpoint
    # (In practice: call your store.get_artifact_content() directly here.)
    raise HTTPException(status_code=501, detail="Integrate into gateway app.py (see docs/GATEWAY_HARDENING.md)")
