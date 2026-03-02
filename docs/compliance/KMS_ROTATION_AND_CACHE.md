# KMS Public Key Cache and Rotation Posture

## Public key cache

Verification uses a two-level strategy:

1) In-process cache keyed by `(kid, key_ref, alg)` with TTL (`DADI_KMS_PUBKEY_CACHE_TTL_SECONDS`, default 3600s).
2) DB ledger table `signing_public_keys` as a historical verification store.

When verifying:
- If cached/ledger key exists, verification does not require a KMS call.
- If missing, gateway calls `kms:GetPublicKey`, then caches and persists it.

If KMS is intermittently unavailable:
- Signing fails closed.
- Verification continues as long as keys are cached or present in the DB ledger.

## Rotation

Rotate by introducing a new KMS key and a new `kid`:
- Set `DADI_SIGNING_KID=new-kid`
- Set `AWS_KMS_KEY_ID=new-key-arn`

Keep old entries active in `signing_public_keys` to verify historical bundles and evidence.

## Healthchecks

- `GET /health/signing` validates signing provider readiness.
- `GET /health/oidc` validates JWKS endpoint reachability (best-effort).
