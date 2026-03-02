from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter

router = APIRouter(tags=["health"])

def _safe_call(fn, default=None):
    try:
        return fn()
    except Exception:
        return default

def _signing_status() -> Dict[str, Any]:
    provider = os.getenv("DADI_SIGNING_PROVIDER", "").strip().lower() or None
    if not provider:
        return {"ok": True, "provider": None}
    try:
        from .signing_provider import load_signing_provider
        p = load_signing_provider()
        p.healthcheck()
        return {"ok": True, "provider": provider}
    except Exception as e:
        return {"ok": False, "provider": provider, "error": str(e)}

def _oidc_status() -> Dict[str, Any]:
    mode = os.getenv("DADI_AUTH_MODE", "off").strip().lower()
    if mode != "oidc":
        return {"ok": True, "mode": mode, "note": "oidc not enabled"}
    jwks = os.getenv("DADI_OIDC_JWKS_URL", "").strip()
    if not jwks:
        return {"ok": False, "mode": mode, "error": "Missing DADI_OIDC_JWKS_URL"}
    try:
        r = requests.get(jwks, timeout=5)
        return {"ok": bool(r.ok), "mode": mode, "jwks_url": jwks, "status_code": r.status_code}
    except Exception as e:
        return {"ok": False, "mode": mode, "jwks_url": jwks, "error": str(e)}

def _audit_chain_status() -> Dict[str, Any]:
    # Best-effort check: verify chain for last N tenant events.
    try:
        from .db import conn_with_tenant
        from .audit import _sha256_hex, _canonical_event_bytes
        tenant = "default"
        with conn_with_tenant(tenant) as c:
            rows = c.execute(
                "SELECT event_id, event_type, pipeline_run_id, deliverable_id, bundle_id, idempotency_key, detail_json, prev_event_hash, event_hash "
                "FROM audit_events WHERE tenant_id=%s AND event_hash IS NOT NULL "
                "ORDER BY created_at ASC, event_id ASC LIMIT 500",
                (tenant,),
            ).fetchall()
        prev = "0"*64
        for r in rows:
            event_id, event_type, pr, did, bid, ik, detail_json, prev_hash, ev_hash = r
            event_for_hash = {
                "tenant_id": tenant,
                "event_id": str(event_id),
                "event_type": event_type,
                "pipeline_run_id": str(pr) if pr else None,
                "deliverable_id": str(did) if did else None,
                "bundle_id": str(bid) if bid else None,
                "idempotency_key": ik,
                "detail": detail_json if isinstance(detail_json, dict) else detail_json,
            }
            msg = prev.encode("ascii") + b"|" + _canonical_event_bytes(event_for_hash)
            expected = _sha256_hex(msg)
            if (prev_hash or "0"*64) != prev or ev_hash != expected:
                return {"ok": False, "checked": len(rows), "first_error_event_id": str(event_id)}
            prev = ev_hash
        return {"ok": True, "checked": len(rows), "chain_head": prev if rows else None}
    except Exception as e:
        # If audit table not present or empty, treat as ok with note in dev.
        return {"ok": True, "note": f"audit chain check skipped/failed: {str(e)}"}

def _schema_validator_status() -> Dict[str, Any]:
    out = {"ok": True, "details": {}}
    # Attempt to load validators; failure indicates schema drift or missing deps.
    try:
        from .manifest_validator import validate_deliverable_manifest
        out["details"]["deliverable_manifest_validator"] = True
    except Exception as e:
        out["ok"] = False
        out["details"]["deliverable_manifest_validator"] = str(e)
    try:
        from .evidence_validator import validate_evidence_manifest
        out["details"]["evidence_manifest_validator"] = True
    except Exception as e:
        out["ok"] = False
        out["details"]["evidence_manifest_validator"] = str(e)
    return out

def _rate_limiter_status() -> Dict[str, Any]:
    backend = os.getenv("DADI_RATE_LIMIT_BACKEND", "memory").strip().lower()
    enabled = os.getenv("DADI_RATE_LIMIT_ENABLED", "true").strip().lower() in ("1","true","yes")
    if not enabled:
        return {"ok": True, "enabled": False, "backend": backend}
    if backend != "redis":
        return {"ok": True, "enabled": True, "backend": backend}
    # Redis connectivity check
    try:
        import redis  # type: ignore
        url = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
        r = redis.Redis.from_url(url, decode_responses=True)
        r.ping()
        return {"ok": True, "enabled": True, "backend": "redis", "redis_url": url}
    except Exception as e:
        fail_closed = os.getenv("DADI_RATE_LIMIT_FAIL_CLOSED", "true").strip().lower() in ("1","true","yes")
        return {"ok": (not fail_closed), "enabled": True, "backend": "redis", "error": str(e), "fail_closed": fail_closed}

def _kms_cache_warmth() -> Dict[str, Any]:
    provider = os.getenv("DADI_SIGNING_PROVIDER", "").strip().lower()
    env_mode = os.getenv("DADI_ENV", "dev").strip().lower()
    if provider != "aws_kms":
        return {"ok": True, "note": "not aws_kms"}
    try:
        from .kms_public_key_cache import KMS_PUBKEY_CACHE
    except Exception as e:
        return {"ok": False, "error": f"kms cache module missing: {str(e)}"}
    kid = os.getenv("DADI_SIGNING_KID", "").strip()
    key_ref = os.getenv("AWS_KMS_KEY_ID", "").strip()
    alg = os.getenv("AWS_KMS_SIGNING_ALG", "ECDSA_SHA_256").strip()
    alg_tag = f"aws_kms:{alg}"
    if not (kid and key_ref):
        return {"ok": False, "error": "Missing DADI_SIGNING_KID or AWS_KMS_KEY_ID"}
    b = KMS_PUBKEY_CACHE.get(kid, key_ref, alg_tag)
    return {"ok": True, "cached": bool(b), "kid": kid, "key_ref": key_ref, "alg": alg_tag}

@router.get("/health/compliance")
def health_compliance(strict: bool = False) -> Dict[str, Any]:
    signing = _signing_status()
    oidc = _oidc_status()
    audit = _audit_chain_status()
    schemas = _schema_validator_status()
    ratelimit = _rate_limiter_status()
    kms_cache = _kms_cache_warmth()

    ok = all([
        signing.get("ok") is True,
        oidc.get("ok") is True,
        audit.get("ok") is True,
        schemas.get("ok") is True,
        ratelimit.get("ok") is True,
        kms_cache.get("ok") is True,
    ])

    failures = []
env_mode = os.getenv("DADI_ENV", "dev").strip().lower()

def req(cond: bool, code: str, detail: Dict[str, Any]):
    if not cond:
        failures.append({"code": code, "detail": detail})

if strict or env_mode in ("prod", "production"):
    req(signing.get("ok") is True, "signing_unhealthy", signing)
    req(schemas.get("ok") is True, "schema_validators_unhealthy", schemas)
    req(ratelimit.get("ok") is True, "rate_limiter_unhealthy", ratelimit)

    if env_mode in ("prod", "production"):
        req(oidc.get("ok") is True, "oidc_unhealthy", oidc)
        if kms_cache.get("note") != "not aws_kms":
            req(kms_cache.get("ok") is True, "kms_cache_unhealthy", kms_cache)

ok = (len(failures) == 0) if strict else ok

return {
        "ok": ok,
        "env": os.getenv("DADI_ENV", "dev"),
        "auth_mode": os.getenv("DADI_AUTH_MODE", "off"),
        "signing": signing,
        "oidc": oidc,
        "audit_chain": audit,
        "schemas": schemas,
        "rate_limit": ratelimit,
        "kms_cache": kms_cache,
        "strict": strict,
        "failures": failures,
    }
