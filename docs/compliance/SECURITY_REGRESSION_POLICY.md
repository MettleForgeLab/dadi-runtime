# Security Regression Policy

Tagged releases must fail closed unless all security gates pass.

## Required gates
- Release manifest verification
- Release attestation verification
- External verifier verification
- Adversarial suite (expect_failure) must confirm tamper detection
- Migrations CI must pass
- Compliance gate CI must pass

## Fail-closed
If any gate fails, the release must not be published.

## Change control
Any change to verifiers, signing envelopes, schemas, authz, or revocation must update this policy and corresponding tests.

