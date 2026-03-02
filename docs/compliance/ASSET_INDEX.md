# Asset Index

This index enumerates compliance artifacts and where they are produced.

## Release assets (GitHub Release)

- `release.zip` — source snapshot for tag
- `RELEASE_MANIFEST.json` — integrity manifest for critical files
- `RELEASE_ATTESTATION.json` — signature over manifest bytes
- `RELEASE_PUBLIC_KEYS.json` — JWKS-like keys for verifying release attestation
- `release-verifier.zip` — self-contained external verifier bundle
- `release-verifier.sha256` — SHA256 digest for verifier bundle
- `release-verifier.attestation.json` — signature over verifier digest
- `SBOM.cdx.json` — CycloneDX SBOM
- `SBOM.spdx.json` — SPDX SBOM
- `PROVENANCE.json` — SLSA-lite provenance
- `PROVENANCE_ATTESTATION.json` — signature over provenance
- `KEY_REVOCATIONS.json` — key revocation list signed by revocation authority
- `REVOCATION_AUTHORITY_PUBLIC_KEYS.json` — public keys for verifying revocations

Produced by:
- `.github/workflows/release.yml`

## Revocation feed (published)

- `REVOCATION_FEED.json` — signed revocation feed
- `KEY_REVOCATIONS.json`
- `REVOCATION_AUTHORITY_PUBLIC_KEYS.json`

Produced by:
- `.github/workflows/publish-revocations.yml`

## Local smoke outputs

- `evidence/` directory:
  - `smoke_report.json`
  - `bundle_downloaded.zip`
  - `bundle_verification_report.json`
  - `audit_excerpt.json`
  - `metrics_excerpt.json`
  - optional chain verify

Produced by:
- `make compliance-smoke`

## Verification tooling

- `tools/release-verifier/audit_verify.py` — one-shot release verification
- `tools/adversarial-suite/` — tamper simulation and fail-closed checks
