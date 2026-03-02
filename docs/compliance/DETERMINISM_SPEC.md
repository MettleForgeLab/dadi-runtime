# Determinism Specification

This specification freezes the determinism model and boundary semantics for the compliance-grade substrate.

It is intended to be implementation-independent, but mapped to enforcement points in this repository.

## Core definitions

### Declared toolchain

The complete set of executable hashes (SHA256), module wiring (e.g., `tools.json`), runtime version or container digest, and relevant OS/architecture identifiers that together define the exact execution environment under which a stage is invoked.

### Canonicalization scope

Canonicalization is defined per-format and guarantees byte-level stability for explicitly declared canonical formats under a declared toolchain.

### Fail-closed

If a stage violates declared invariants, it emits no artifact and produces a deterministic error record; execution halts at that boundary.

### Trust policy enforcement surface

Trust policy is evaluated at delta application time and gates file-level mutation before artifact replacement within the artifact graph.

## Determinism boundary

Determinism is defined relative to a declared toolchain, not to an abstract notion of identical computation.

Given:
- identical inputs
- identical invocation parameters
- an identical declared toolchain

The system produces byte-identical outputs for declared canonical formats.

Outside that boundary, no determinism is claimed.

## Artifact model

An artifact is:
- canonicalized (for declared canonical formats)
- hash-identified (SHA256 of canonical bytes)
- stage-bounded (emitted only at explicit boundaries)
- rerunnable (replay under identical boundary produces identical bytes)
- governed by explicit mutation rules (no in-place mutation)

Artifacts are the unit of reproducibility.

## Closure modes

Release objects explicitly declare completeness criteria:

- `closure_mode = stage_runs_v1`

Meaning:
- the manifest artifact list includes all artifacts referenced directly by `stage_runs` (inputs/outputs/toolchain/prompt/errors) plus deliverable pointer artifacts and rendered bytes.

Closure semantics must not change without a versioned new mode.

## Signed manifests

### Bundle manifest

- schema: `deliverable_manifest-v1`
- signed over canonical JSON bytes of the unsigned manifest
- signature envelope: `alg`, `kid`, `sig` (+ optional `key_ref`)

### Evidence manifest

- schema: `deliverable_evidence_manifest-v1`
- signed over canonical JSON bytes of the unsigned manifest
- evidence includes pointers to:
  - deliverable_record artifact
  - bundle manifest hash and bundle hash
  - audit chain verify snapshot (best-effort)
  - metrics snapshot (best-effort)

### Release manifest attestation

- `RELEASE_MANIFEST.json` is an integrity manifest for the software release
- `RELEASE_ATTESTATION.json` signs the canonical bytes of `RELEASE_MANIFEST.json`

## Enforcement map (repository)

- Declared toolchain concept: manifest artifacts + toolchain hashing (pipeline runtime)
- Canonicalization: canonical JSON serialization rules used for signing and hashing
- Fail-closed boundaries: JSON Schema validation at stage boundaries and manifest creation
- Closure verification: `/bundle/verify` validates `closure_mode`
- Signed manifests: signing provider + verifier and schema validators
- Audit chain integrity: `audit_events` hash chaining and `/audit/verify-chain`
- Compliance gate: `/health/compliance?strict=true`

## Compatibility rules

A change is breaking if it:
- changes canonicalization rules for an existing canonical format
- alters the meaning of an existing closure_mode
- invalidates previously valid manifest/evidence schema instances
- changes signature envelope fields required for verification

Breaking changes require:
- new schema_version identifiers or new closure_mode identifiers
- migration strategy for verifiers and external auditors
