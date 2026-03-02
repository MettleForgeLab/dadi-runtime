# DADI-Engine Monorepo (Assembled Packs)

This monorepo assembles the current DADI-Engine reference stack into a single repository layout.

## Layout

- `whitepaper/` — DADI-Engine White Paper v0.1.0 (exportable from canvas)
- `schemas/` — Draft 2020-12 JSON Schemas (v1.1)
- `services/`
  - `gateway/` — unified FastAPI surface (artifacts, lineage, cache, plans)
  - `artifact-store/` — artifact store + lineage graph + memoization (pack)
  - `orchestrator/` — deterministic stage orchestration (pack)
  - `regen-planner/` — regeneration planner + explain (pack)
  - `llm-adapter/` — deterministic envelope + capture/replay/drift (pack)
- `tools/`
  - `validator/` — jsonschema validator pack
  - `regress/` — regression harness (fixtures: record/verify/diff)
- `ui/`
  - `artifact-browser/` — minimal Next.js UI for artifacts, lineage, plans, diff
- `deploy/`
  - `reference/` — docker-compose happy path + seed script
- `posture/`
  - `confidentiality-security/` — gateway hardening + policy + safe export

## Next steps

1) Add Makefile workflows at repo root (planned next).
2) Add minimal integration tests protecting invariants (planned after workflows).


## Workflows

Common developer flows:

Start full stack:

```bash
make up
```

Seed demo data:

```bash
make seed
```

Create regeneration plan:

```bash
make plan OLD=<old_prompt_sha> NEW=<new_prompt_sha>
```

Record regression fixture:

```bash
make regress RUN=<pipeline_run_id> OUT=fixture.zip
```

Verify fixture:

```bash
make verify FIXTURE=fixture.zip
```

Safe (manifest-only) export:

```bash
make export-safe FIXTURE=fixture.zip OUT=safe.zip
```

Shut down stack:

```bash
make down
```


## Tests (Integration)

After starting the stack:

```bash
pip install -r requirements-dev.txt
pytest
```

These tests validate:

- Artifact immutability (same bytes → same SHA256)
- Cache memoization roundtrip
- Regeneration planner `/explain` shape stability


## Renderer

- `services/renderer/` — DOCX-first deterministic rendering stage (Stage 06).


## Drift (Run Diff)

Gateway provides `GET /runs/diff?run_a=<id>&run_b=<id>` to compare stage-level outputs.


## Bundle verification

```bash
make bundle-verify BUNDLE=<bundle_sha256> OUT=bundle_report.json
```


## Seed state

The reference seed script writes `.seed_state.json` at repo root for integration tests.


## Adversarial tests

- `tests/test_adversarial_integrity.py` exercises tamper cases:
  - tampered manifest signature fails server verify
  - tampered bundle zip is detected offline


## Cross-tenant adversarial tests

- `tests/test_cross_tenant_adversarial.py` exercises tenant boundary and scope gates.


## Idempotency

Mutation endpoints support `Idempotency-Key` for safe retries and concurrent requests.


## Compliance integrations

- OIDC/JWKS auth (DADI_AUTH_MODE=oidc)
- AWS KMS signing provider for bundle manifests (DADI_SIGNING_PROVIDER=aws_kms)
- Bundle download policy (sent-only) via /deliverables/{deliverable_id}/bundles/{bundle_id}/download


## Local IdP stub

A local OIDC IdP stub is included at `services/idp_stub/` and runs on port 9000 in the reference compose.
It serves JWKS at `/.well-known/jwks.json` and issues tokens at `/token`.


## Dev signing provider

Reference deployment defaults to `DADI_SIGNING_PROVIDER=dev_ed25519` for local runs. Production requires `aws_kms` with `DADI_ENV=prod`.


## Compliance dev loop

See `RUNBOOK_COMPLIANCE.md` and use:

- `make compliance-up`
- `make compliance-seed`
- `make compliance-smoke`


## Evidence

Evidence packets can be generated for sent deliverables via `POST /deliverables/{deliverable_id}/evidence` (scope: deliverable:evidence).


## Production profile

A production template compose file is provided at `deploy/reference/docker-compose.prod.yml`.
See `docs/compliance/PROD_SETUP.md`.


## Revocation and retention

- Revoke bundle: `POST /deliverables/{deliverable_id}/bundles/{bundle_id}/revoke`
- Revoke evidence: `POST /deliverables/{deliverable_id}/evidence/{evidence_id}/revoke`
- Sweep retention: `python scripts/retention_sweep.py`


## Authorization

See `docs/compliance/AUTHZ_MATRIX.md` and `tests/test_authz_matrix_enforcement.py`.


## Compliance Gate GitHub Actions

A CI workflow is provided at `.github/workflows/compliance-gate.yml`.


## Threat model

See `docs/compliance/THREAT_MODEL.md`.


## Release manifest

This release includes `RELEASE_MANIFEST.json` and `scripts/verify_release_manifest.py` for integrity verification.


## Release attestation

This release includes `RELEASE_ATTESTATION.json` and scripts to sign/verify it:
- `scripts/sign_release_manifest.py`
- `scripts/verify_release_attestation.py`

In production, sign using the configured signing provider (e.g., AWS KMS). In dev, a self-contained Ed25519 attestation can be used.


## External release verification

See `tools/release-verifier/`.


## Release public keys

Releases may include `RELEASE_PUBLIC_KEYS.json` for third-party verification.


## Release assets

See `docs/compliance/RELEASE_ASSETS.md`.


## Release key policy

See `docs/compliance/RELEASE_KEY_POLICY.md`.


## Release readiness

See `docs/compliance/RELEASE_READINESS.md`.


## Dev release workflow

A manual dev release workflow is provided at `.github/workflows/dev-release.yml`.


## Release revocation

Releases include `RELEASE_STATUS.json`. External verifiers must ensure `status == active`.


## Compromise response

See `docs/compliance/COMPROMISE_RESPONSE.md`.


## Stability and determinism

See:
- `docs/compliance/STABILITY_POLICY.md`
- `docs/compliance/DETERMINISM_SPEC.md`


## Adversarial suite

See `tools/adversarial-suite/`.


## Security regression policy

See `docs/compliance/SECURITY_REGRESSION_POLICY.md`.


## SBOM and provenance

See `docs/compliance/SBOM_AND_PROVENANCE.md`.


## One-shot release audit verification

Copy/paste:

```bash
python tools/release-verifier/audit_verify.py --release-dir . --out audit_report.json
```

This verifies:
- release status (active)
- manifest hashes
- release attestation
- SBOM + provenance contracts
- external verifier
- adversarial tamper detection


## Verifier bundle

Releases publish `tools/release-verifier/release-verifier.zip` as a release asset.


## Runbook

See `docs/compliance/RUNBOOK.md`.


## Asset index

See `docs/compliance/ASSET_INDEX.md`.


## Bootstrap

```bash
make bootstrap
```
