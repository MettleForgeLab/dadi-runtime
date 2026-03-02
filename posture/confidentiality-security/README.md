# Confidentiality + Security Posture Pack (Financial-Services Ready)

This pack hardens the DADI Gateway and operational tooling for confidentiality-sensitive deployments.

Scope:
- Add an auth boundary at the gateway (bearer token middleware).
- Enforce "deny-by-default" for endpoints returning artifact bytes.
- Add structured logging with explicit no-content rules.
- Add safe export mode for regression fixtures (manifest-only).
- Provide concise posture docs and runbook guidance.

This pack does not add new architectural layers. It hardens the existing surfaces.

## Contents

- `gateway_patch/`:
  - `auth.py` — bearer token middleware + policy hooks
  - `logging.py` — structured logging helpers (no content logs)
  - `app_patch.py` — drop-in FastAPI app wrapper showing how to integrate auth/logging
- `policy/`:
  - `policy.example.json` — gateway policy knobs (content access, export controls)
- `scripts/`:
  - `safe_fixture_export.py` — export *manifest-only* fixture packs (no bytes)
- `docs/`:
  - `CONFIDENTIALITY_POSTURE.md` — operational rules + threat boundaries
  - `GATEWAY_HARDENING.md` — integration steps for the gateway repo

## Quick integration approach

1) Copy `gateway_patch/auth.py` and `gateway_patch/logging.py` into your gateway repo.
2) Apply the changes described in `docs/GATEWAY_HARDENING.md`.
3) Create a `policy.json` from `policy/policy.example.json`.
4) Run the gateway with:
   - `DADI_AUTH_MODE=bearer`
   - `DADI_BEARER_TOKEN=<secret>`
   - `DADI_POLICY_PATH=/path/to/policy.json`

## Notes

- This is intentionally minimal and deployable under NDA conditions.
- Identity management, encryption, and network security remain out-of-scope; this pack helps you avoid accidental leakage via APIs and logs.
