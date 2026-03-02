# Compliance Health Endpoint

`GET /health/compliance` returns a structured snapshot of compliance posture:

- signing provider readiness
- OIDC JWKS reachability (best-effort)
- audit hash chain integrity (best-effort)
- schema validator load status
- rate limiter backend reachability
- KMS public key cache warmth (when aws_kms is configured)

This endpoint is intended for internal monitoring and deployment verification.
