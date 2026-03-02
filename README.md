# DADI Runtime

**Deterministic Artifact Runtime**

**Status:** Public Release  
**Version:** v0.2.x  
**Scope:** Deterministic artifact execution, plan orchestration, lineage tracking, structural comparison, and release verification  
**Attribution:** Mettle Forge Lab

DADI Runtime is a deterministic artifact execution substrate that enforces artifact identity, lineage, and reproducible plan execution. It does not define governance, authority, or constitutional invariants.

---

## What DADI Is

DADI provides:

- **Content-addressed artifact identity** (SHA256 over canonical bytes)
- **Deterministic stage boundaries** with fail-closed validation
- **Artifact lineage** as a directed graph of derivation
- **Plan-based execution semantics** (describe → execute → replay within declared constraints)
- **Deterministic structural comparison** of canonical artifacts
- **Release verification surfaces** (manifest + attestation)

DADI is an execution engine and an artifact graph.

---

## What DADI Is Not

DADI does **not**:

- Define governance doctrine
- Define authority structures
- Legislate invariants beyond declared execution boundaries
- Guarantee semantic correctness of artifact content
- Replace organizational decision systems

DADI executes under declared constraints. Governance and authority must be externalized.

---

## Core Concepts

### Artifact
A canonicalized, hash-identified output produced at a declared stage boundary.

- Identity: SHA256 of canonical bytes
- Immutable by identity
- Addressable and replayable
- Valid only if schema validation passes

Artifacts are the unit of truth in DADI.

### Plan
A plan is a first-class description of intended execution.

A plan may be:

- Explained (structural description of intended changes)
- Executed deterministically within declared boundaries
- Replayed under identical toolchain and input conditions

Plans do not expand determinism beyond declared constraints.

### Lineage
Artifacts form a directed graph:

- Nodes: artifacts (content-identified)
- Edges: declared derivation relationships
- Traversable upstream and downstream

Lineage is structural, not interpretive. It reflects declared execution and mutation boundaries.

### Diff
Diff represents a deterministic structural delta between two canonical artifacts.

- Computed from canonicalized representations where applicable
- Content-based, not location-based
- Useful for audit, replay reasoning, and artifact comparison

Diff does not assert semantic meaning. It reflects structural change.

---

## Determinism Model

Determinism applies only within declared execution boundaries.

Given:

- Identical inputs
- Identical invocation parameters
- Identical declared toolchain/runtime boundary

DADI should produce byte-identical canonical artifacts.

Outside declared boundaries, no determinism is claimed.

Operational hardening does not widen this envelope.

---

## Security Posture (Boundary-Focused)

- Artifact identity is content-derived.
- Stage contracts fail closed on schema violation.
- Mutation requires explicit base-hash agreement.
- Audit events are hash-chained and tamper-evident.
- Release artifacts are verifiable via manifest and attestation surfaces.

DADI does not embed master signing keys.  
Authority and key custody are external responsibilities.

---

## Release Verification

Each release publishes:

- A release manifest
- A release attestation
- Public verification keys
- A verifier bundle capable of independent validation

Verification is designed to fail closed on mismatch or tamper.

Determinism and verification apply to artifacts and releases under declared boundaries.

---

## Deployment (Reference Stack)

A minimal reference stack is provided for local execution and inspection.

Typical surfaces include:

- Gateway API
- Artifact Browser (inspection UI)
- Supporting services

The Artifact Browser is a tooling surface for inspection.  
It is not the authority layer and does not define invariants.

Consult `deploy/reference/` for the current reference configuration.

---

## Audience

DADI is intended for:

- Systems engineers
- Reproducibility and verification teams
- Developers building deterministic artifact pipelines
- Auditors evaluating replayability and artifact integrity

---

## Status

Current baseline: **v0.2.x**

Invariant-bearing semantics are frozen at this version line.

Governance, authority management, and lifecycle policy are intentionally external to this repository.
