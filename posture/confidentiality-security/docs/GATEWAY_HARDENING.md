# Gateway Hardening Guide

This guide describes minimal changes to harden the DADI Gateway for confidentiality-sensitive deployments.

## 1) Add middleware

In your gateway `app.py`:

- Add `StructuredLoggingMiddleware` to log request/response metadata without payloads.
- Add `BearerAuthMiddleware` to enforce bearer-token access.

Environment variables:
- `DADI_AUTH_MODE=bearer`
- `DADI_BEARER_TOKEN=<secret>`
- `DADI_POLICY_PATH=/path/to/policy.json`

## 2) Gate content endpoints

Modify `GET /artifacts/{sha256}/content`:

- Reject if policy disables content.
- Reject if missing explicit opt-in header (default `X-DADI-Allow-Content: true`).
- Reject if auth is not enabled (in environments where content access requires auth).

## 3) Confirm no-content logging

- Ensure you do not log request bodies in exception handlers.
- Ensure structured logs redact authorization headers.

## 4) Fixture export mode

Prefer manifest-only exports:
- Use `scripts/safe_fixture_export.py` to generate a fixture manifest without bytes.

## 5) Deployment notes

- Place the gateway behind TLS termination.
- Put it behind a network boundary (private subnet / VPN / zero trust proxy).
- Rotate bearer token; replace with SSO/OIDC when integrating with enterprise identity.
