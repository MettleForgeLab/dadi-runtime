# Compromise Response Plan

This document defines response steps if a release signing key or release artifact is compromised.

## Scenarios

- AWS KMS key compromise
- IAM role misuse
- Malicious or incorrect release published

## Immediate Actions

1) Revoke affected release:
   ```bash
   python scripts/revoke_release.py --reason "KMS key compromise" --superseded-by vX.Y.Z
   ```

2) Publish updated `RELEASE_STATUS.json` and regenerate release artifacts.

3) Rotate signing key:
   - Create new KMS key
   - Update `AWS_KMS_KEY_ID` and `DADI_SIGNING_KID`
   - Publish new release

4) Preserve old public keys for historical verification.

## Communication

- Publish advisory with affected version numbers.
- Provide superseding version reference.

## Verification

External verifiers must check:
- `RELEASE_STATUS.json`
- `RELEASE_ATTESTATION.json`
- `RELEASE_MANIFEST.json`
