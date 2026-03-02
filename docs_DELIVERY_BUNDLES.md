# Delivery Bundles + Signed Manifests

## Summary

A deliverable bundle is a deterministic ZIP artifact containing:
- `manifest.json` (signed)
- `artifacts/<sha256>` (bytes for included artifacts)

The manifest is canonical JSON signed via HMAC-SHA256 over the unsigned manifest bytes.

## Endpoints

- `POST /deliverables/{deliverable_id}/bundle`
- `GET /deliverables/{deliverable_id}/bundles`
- `POST /deliverables/{deliverable_id}/bundle/verify`

## Determinism boundary

Bundle bytes are deterministic relative to:
- included artifact bytes
- canonical manifest bytes
- fixed zip entry ordering

Signing uses `DADI_BUNDLE_SIGNING_SECRET`.

## Non-claims

HMAC signing here is a deployable stub. For production, replace with an asymmetric signing scheme (Ed25519) and key rotation policy.


## Signature format

Manifest includes:

- `signature.alg`
- `signature.kid`
- `signature.sig` (base64url)

## Env

- `DADI_BUNDLE_SIGNING_ALG` (`ed25519` or `hmac-sha256`)
- `DADI_BUNDLE_SIGNING_KID`
- HMAC: `DADI_BUNDLE_SIGNING_SECRET` or `DADI_HMAC_SECRETS_JSON`
- Ed25519: `DADI_ED25519_PUBLIC_KEYS_JSON`, `DADI_ED25519_PRIVATE_KEYS_JSON`


## Closure mode

Manifests include `closure_mode` to make completeness criteria explicit.

- `stage_runs_v1`: includes artifacts referenced directly by `stage_runs` (inputs/outputs/toolchain/prompt/errors) plus deliverable pointer artifacts and rendered bytes.
