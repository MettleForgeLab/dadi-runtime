# Stability Policy

This policy defines what constitutes a breaking change and how versioning must be managed for compliance-grade deployments.

The goal is to prevent silent drift of guarantees over time.

## Versioning scheme

The repository uses semantic versioning with an explicit compliance flavor tag:

- `vMAJOR.MINOR.PATCH-compliance`

Where:
- **MAJOR**: breaking changes to invariants, schemas, signing, authz, determinism boundary, or migration contract
- **MINOR**: additive features that do not break existing guarantees
- **PATCH**: bug fixes and internal changes that do not alter externally observable behavior

## Frozen invariants

The following invariants must not change without a **MAJOR** bump and an explicit change log entry:

1. **Artifact immutability**  
   Artifacts are hash-identified, immutable content-addressed objects.

2. **Determinism boundary**  
   Determinism is defined relative to:
   - declared toolchain
   - invocation parameters
   - canonicalization rules for declared formats

3. **Fail-closed execution boundaries**  
   Boundary violations emit no artifact and halt at that boundary.

4. **Signed release objects**  
   - bundle manifests are signed
   - evidence manifests are signed
   - release manifests are attested (software release signing)

5. **Export governance**  
   - sent-only download for bundles and evidence
   - scope-gated through dedicated endpoints
   - revoked objects cannot be downloaded

6. **Tenant isolation**  
   tenant_id derives from token claim and is enforced via RLS + tenant-scoped queries.

7. **Tamper-evident audit logging**  
   audit events are hash-chained and verifiable.

## What is a breaking change (MAJOR)

Any change that causes an existing verifier or consumer to fail or to interpret outputs differently, including:

### API contract
- Removing endpoints
- Changing response shapes in a way that breaks clients
- Changing required scopes for an endpoint (either tightening or loosening) without migration strategy

### Schemas
- Changing a JSON Schema in a way that invalidates previously valid artifacts or manifests
- Renaming schema_version identifiers

### Signing / verification
- Changing signature envelope fields
- Changing the signing algorithm without supporting legacy verification
- Changing `kid` semantics

### Determinism / canonicalization
- Changing canonicalization rules for a declared canonical format
- Changing closure_mode semantics
- Changing the determinism boundary definition

### Database schema / migration contract
- Editing historical SQL files without bumping checksums
- Changing baseline migration order
- Removing required columns/indexes

## What is a minor change (MINOR)

- Adding new endpoints that do not weaken policy
- Adding new optional fields to schemas (and keeping old valid)
- Adding new closure modes as opt-in (no behavior change for existing mode)
- Adding new verifiers or tooling

## What is a patch (PATCH)

- Bug fixes that preserve external behavior
- Performance improvements
- Internal refactors
- Documentation updates

## Change control requirements

For any change touching:
- auth scopes
- download policy
- signing provider behavior
- schema versions
- closure verification
- audit chain hashing
- migrations/checksums

Required:
- update `CHANGELOG.md`
- update `AUTHZ_MATRIX.md` (if auth/policy changes)
- update `THREAT_MODEL.md` (if threat boundaries change)
- add/modify tests
- pass `make compliance-gate` and migrations CI
