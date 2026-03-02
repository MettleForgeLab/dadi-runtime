# Release Verifier (Standalone)

This tool verifies a DADI release artifact **without** running the gateway or database.

It verifies:

1) `RELEASE_MANIFEST.json` file hashes and tree hash
2) `RELEASE_ATTESTATION.json` signature over the canonical bytes of `RELEASE_MANIFEST.json`

## Usage

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python verify_release.py --release-dir /path/to/unzipped/release --public-keys release_public_keys.json
```

Where `release_public_keys.json` is a JWKS-like file:

```json
{
  "keys": [
    {"kid":"k1","kty":"OKP","crv":"Ed25519","x":"<base64url>","alg":"EdDSA","use":"sig"},
    {"kid":"k2","kty":"RSA","n":"...","e":"...","alg":"RS256","use":"sig"}
  ]
}
```

Exit codes:
- 0: ok
- 2: failed


## One-shot audit verification

```bash
python tools/release-verifier/audit_verify.py --release-dir . --out audit_report.json
```


## Quick start

Linux/macOS:

```bash
./run.sh --release-dir /path/to/release --out audit_report.json
```

Windows PowerShell:

```powershell
./run.ps1 -ReleaseDir /path/to/release -Out audit_report.json
```
