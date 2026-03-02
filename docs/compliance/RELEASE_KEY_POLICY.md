# Release Signing Key Policy (AWS KMS)

Tagged releases (`v*`) are signed using AWS KMS in GitHub Actions via GitHub OIDC role assumption.

No long-lived AWS credentials are stored in GitHub secrets.

## Required GitHub Secrets

- `AWS_ROLE_TO_ASSUME` — IAM role ARN to assume via OIDC
- `AWS_REGION` — KMS region
- `AWS_KMS_KEY_ID` — Asymmetric signing key ARN/ID
- `AWS_KMS_SIGNING_ALG` — e.g., `ECDSA_SHA_256` (optional if defaulted)
- `DADI_SIGNING_KID` — key identifier embedded in signatures

## IAM Policy (minimum)

The assumed role must allow:

- `kms:Sign` on the key
- `kms:GetPublicKey` on the key

## Rotation

Rotate by changing `AWS_KMS_KEY_ID` and `DADI_SIGNING_KID` for subsequent releases.
Preserve historical `RELEASE_PUBLIC_KEYS.json` to verify older releases.

## Verification

Each GitHub Release publishes:
- `release.zip`
- `RELEASE_MANIFEST.json`
- `RELEASE_ATTESTATION.json`
- `RELEASE_PUBLIC_KEYS.json`

Third parties can verify using:
- `tools/release-verifier/verify_release.py`
