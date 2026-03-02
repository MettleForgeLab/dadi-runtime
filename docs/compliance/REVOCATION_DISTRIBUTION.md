# Revocation Distribution

This system supports two verification profiles.

## Profile: archival (default)

- Intended for long-term verification and air-gapped environments.
- Uses the revocation artifacts shipped with a release:
  - `KEY_REVOCATIONS.json`
  - `REVOCATION_AUTHORITY_PUBLIC_KEYS.json`
- Online feed is optional.

## Profile: procurement (strict)

- Intended for third-party intake / deployment approval.
- Requires a current signed revocation feed:
  - `REVOCATION_FEED.json`
- Fails closed if the feed is unavailable or too old.

## Verifier flags

`audit_verify.py` supports:

- `--profile archival|procurement`
- `--revocation-feed-url <url>`
- `--offline`
- `--require-fresh-revocations`
- `--max-feed-age-hours N` (enforced when `--require-fresh-revocations` is true)

## Publishing

Use `.github/workflows/publish-revocations.yml` to publish the feed to `gh-pages` (or modify to publish to S3/GCS).


## GitHub Pages URL

Default URL format:

- `https://<org>.github.io/<repo>/REVOCATION_FEED.json`
