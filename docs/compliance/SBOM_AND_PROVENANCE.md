# SBOM and Provenance

Tagged releases publish:

- `SBOM.cdx.json` (CycloneDX)
- `SBOM.spdx.json` (SPDX)
- `PROVENANCE.json` (SLSA-lite provenance)
- `PROVENANCE_ATTESTATION.json` (signature over provenance)

Generation:
- `scripts/generate_sbom.py`
- `scripts/generate_provenance.py`

Signing:
- `scripts/sign_provenance.py`

Verification:
- `scripts/verify_provenance.py`
