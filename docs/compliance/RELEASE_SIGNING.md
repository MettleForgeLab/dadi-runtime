# Release Signing

This release includes:

- `RELEASE_MANIFEST.json`
- `RELEASE_ATTESTATION.json`

External verification:
- `tools/release-verifier/verify_release.py`

Publish public keys (JWKS-like JSON) keyed by `kid` to allow third-party verification.


## Production

Tagged releases are signed in CI using AWS KMS via GitHub OIDC.
See `docs/compliance/RELEASE_KEY_POLICY.md`.
