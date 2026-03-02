# Production Setup (Compliance Profile)

This document describes the production posture requirements.

## Required posture

- `DADI_ENV=prod`
- `DADI_AUTH_MODE=oidc`
  - `DADI_OIDC_ISSUER`
  - `DADI_OIDC_AUDIENCE`
  - `DADI_OIDC_JWKS_URL`
- Postgres RLS enabled and gateway sets `SET app.tenant_id = <tenant>` for every connection/transaction.
- `DADI_SIGNING_PROVIDER=aws_kms`
  - `AWS_REGION`
  - `AWS_KMS_KEY_ID` (asymmetric signing key)
  - `DADI_SIGNING_KID` (application-level key label)
  - optional `AWS_KMS_SIGNING_ALG` (default ECDSA_SHA_256)

## Recommended

- TLS termination in front of gateway
- Network isolation (private subnets / VPN / zero trust proxy)
- Rate limiting on bytes endpoints and bundle creation/download
- Secret management for all credentials

## Compose

Use:

- `deploy/reference/docker-compose.prod.yml`

This file removes the local IdP stub and dev signer. It is a template; wire to real IdP and real AWS KMS.
