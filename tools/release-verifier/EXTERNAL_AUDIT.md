# External Audit Verification

This verifier bundle is intended for third-party verification of a tagged release.

## What you need

From the GitHub Release assets:

- `release.zip`
- `RELEASE_MANIFEST.json`
- `RELEASE_ATTESTATION.json`
- `RELEASE_PUBLIC_KEYS.json`
- `release-verifier.zip`

## Steps

0) Verify the verifier bundle itself:

```bash
sha256sum -c release-verifier.sha256
python ../release/scripts/verify_asset_attestation.py --asset release-verifier.zip --attestation release-verifier.attestation.json --public-keys ../release/RELEASE_PUBLIC_KEYS.json
```


1) Unzip the release:

```bash
unzip release.zip -d release
cd release
```

2) Unzip the verifier bundle:

```bash
unzip release-verifier.zip -d verifier
```

3) Run verification (Linux/macOS):

```bash
cd verifier
./run.sh --release-dir ../release --out audit_report.json
```

Windows PowerShell:

```powershell
cd verifier
./run.ps1 -ReleaseDir ../release -Out audit_report.json
```

## Output

`audit_report.json` contains a single machine-readable verdict:

- `ok: true` means the release is active, internally consistent, cryptographically verified, and tamper-detection gates work.
- `ok: false` means verification failed; see `checks[]` for the failing step.


## Key revocation list

If `KEY_REVOCATIONS.json` is present, it is verified using `REVOCATION_AUTHORITY_PUBLIC_KEYS.json`.


## Freshness (optional)

To use a current revocation feed (if published), run:

```bash
python audit_verify.py --release-dir ../release --revocation-feed-url https://<your-domain>/REVOCATION_FEED.json --require-fresh-revocations
```


## Verification profiles

Archival (offline-friendly):

```bash
python audit_verify.py --release-dir ../release
```

Procurement (requires fresh revocations):

```bash
python audit_verify.py --release-dir ../release --profile procurement --revocation-feed-url https://<your-domain>/REVOCATION_FEED.json --max-feed-age-hours 72
```
