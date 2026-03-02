# Bundle Verify CLI

Portable verifier for delivery bundles.

## Usage

Set env:
- `NEXT_PUBLIC_API_BASE` (gateway base URL, e.g. http://localhost:8000)
- `NEXT_PUBLIC_AUTH_TOKEN` (Bearer JWT)

Verify by bundle artifact hash:

```bash
python bundle_verify.py --bundle-sha <sha256> --out report.json
```

Verify using a local zip file:

```bash
python bundle_verify.py --bundle-zip path/to/bundle.zip --out report.json
```

Ed25519 offline verification requires:
- `DADI_ED25519_PUBLIC_KEYS_JSON` (kid->b64url pub key)

HMAC verification requires:
- `DADI_HMAC_SECRETS_JSON` or `DADI_BUNDLE_SIGNING_SECRET` + `DADI_BUNDLE_SIGNING_KID`
