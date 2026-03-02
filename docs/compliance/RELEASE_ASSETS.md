# Release Assets

A tagged release publishes the following assets:

- `release.zip` — full source snapshot for the tag
- `RELEASE_MANIFEST.json` — integrity manifest of critical files
- `RELEASE_ATTESTATION.json` — signature over the canonical bytes of `RELEASE_MANIFEST.json`
- `RELEASE_PUBLIC_KEYS.json` — JWKS-like public keys needed to verify the attestation

## Verify

1) Unzip `release.zip`

2) Verify the manifest hashes:

```bash
python scripts/verify_release_manifest.py
```

3) Verify the attestation:

```bash
python scripts/verify_release_attestation.py
```

4) External verification (no gateway/DB):

```bash
python tools/release-verifier/verify_release.py --release-dir . --public-keys RELEASE_PUBLIC_KEYS.json
```

## Notes

- `kid` identifies the signing key used for this release.
- Keep historical `RELEASE_PUBLIC_KEYS.json` to verify old releases.
