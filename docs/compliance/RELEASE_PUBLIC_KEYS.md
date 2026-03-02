# Release Public Keys

Releases may include:

- `RELEASE_PUBLIC_KEYS.json`

This is a JWKS-like file containing the public key(s) needed to verify:

- `RELEASE_ATTESTATION.json`

## Generation

- `scripts/export_release_public_keys.py`

Modes:
- dev_ed25519: requires `RELEASE_ED25519_PUBLIC_KEY_B64URL`
- aws_kms: requires AWS creds and `AWS_KMS_KEY_ID` (or uses `signature.key_ref`)

## External verification

Use `tools/release-verifier/verify_release.py` with `RELEASE_PUBLIC_KEYS.json` from the same release.
