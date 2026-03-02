# Release Readiness

This checklist documents the prerequisites for a compliance-grade release.

## AWS and GitHub OIDC

1) Create an IAM role with a trust relationship for GitHub Actions OIDC for this repo/org.
2) Grant the role permissions:
   - `kms:Sign`
   - `kms:GetPublicKey`
   on the configured KMS key.

Required secrets:
- `AWS_ROLE_TO_ASSUME`
- `AWS_REGION`
- `AWS_KMS_KEY_ID`
- `DADI_SIGNING_KID`
- `REVOCATION_FEED_URL` — canonical URL to `REVOCATION_FEED.json` used for procurement-mode verification
- optional `AWS_KMS_SIGNING_ALG`

## KMS key requirements

- Asymmetric signing key (ECC P-256 or RSA as per policy)
- Rotation plan defined (kid/key_ref changes across releases)

## Release artifacts

A tagged release publishes:
- `release.zip`
- `RELEASE_MANIFEST.json`
- `RELEASE_ATTESTATION.json`
- `RELEASE_PUBLIC_KEYS.json`

Third parties verify with:
- `tools/release-verifier/verify_release.py`

## Failure posture

Release workflow is fail-closed:
- if required secrets are missing, the workflow fails early
- if attestation verification fails, the release is not published


### GitHub Pages (recommended)

Set `REVOCATION_FEED_URL` to your GitHub Pages feed URL:

- `https://<org>.github.io/<repo>/REVOCATION_FEED.json`

This is published by `.github/workflows/publish-revocations.yml`.
