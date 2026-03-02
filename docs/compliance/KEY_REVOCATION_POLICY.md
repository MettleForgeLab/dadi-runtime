# Key Revocation Policy

Releases publish a signed key revocation list:

- `KEY_REVOCATIONS.json`

The revocation list is signed by a **revocation authority** key, distinct from the release signing key.

## Revocation authority

- `REVOCATION_AUTHORITY_PUBLIC_KEYS.json` contains public key(s) used to verify revocations.
- Compromise of the release signing key must not prevent publishing valid revocations.

## Verification

`tools/release-verifier/audit_verify.py` verifies:
- `KEY_REVOCATIONS.json` signature using `REVOCATION_AUTHORITY_PUBLIC_KEYS.json`
- rejects releases signed by revoked `kid` values
