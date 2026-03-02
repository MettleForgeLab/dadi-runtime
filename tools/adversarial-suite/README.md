# Adversarial Suite (Fail-Closed Validation)

This suite intentionally tampers with release artifacts and schema inputs to confirm the system fails closed.

## What it tests

1) Release tamper:
- modify `RELEASE_MANIFEST.json` (byte flip)
- modify a critical file and ensure manifest verification fails
- modify `RELEASE_STATUS.json` to active after revocation
- modify `RELEASE_ATTESTATION.json`

2) Key mismatch:
- replace `RELEASE_PUBLIC_KEYS.json` with incompatible key material

3) SQL drift:
- modify a baseline SQL file and ensure checksum enforcement would fail in prod mode

## How to run

Run against an **unzipped release directory**:

```bash
python tools/adversarial-suite/run_all.py --release-dir .
```

Expected outcome: the suite reports PASS when verifiers correctly FAIL on tampered inputs.

## Exit codes
- 0: all adversarial checks behaved as expected
- 2: an adversarial check did not fail as expected
