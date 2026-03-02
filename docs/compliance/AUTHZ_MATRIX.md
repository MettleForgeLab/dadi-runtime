# Authorization Matrix

This document defines the required authorization conditions for high-risk endpoints.

Notation:
- **Auth**: valid Bearer token required
- **Scope**: required scope claim (space-delimited `scope` claim)
- **State**: deliverable lifecycle requirement
- **Audit**: whether the endpoint emits audit receipts/events

## Artifact bytes

| Endpoint | Method | Auth | Scope | State | Notes |
|---|---:|---:|---|---|---|
| `/artifacts/{sha256}/content` | GET | Yes | `artifact:read_bytes` | n/a | Direct download of bundle/evidence zips is blocked. |
| `/artifacts` | POST | Yes | (none) | n/a | Request size limited; consider separate write scope in strict deployments. |

## Deliverables lifecycle

| Endpoint | Method | Auth | Scope | State | Audit |
|---|---:|---:|---|---|---:|
| `/deliverables` | POST | Yes | (none) | n/a | deliverable_created |
| `/deliverables/{id}/finalize` | POST | Yes | (none) | n/a | deliverable_finalized |
| `/deliverables/{id}/mark_sent` | POST | Yes | (none) | must be final/draft | (optional) |
| `/deliverables/{id}/supersede` | POST | Yes | (none) | n/a | (optional) |

## Bundles

| Endpoint | Method | Auth | Scope | State | Audit |
|---|---:|---:|---|---|---:|
| `/deliverables/{id}/bundle` | POST | Yes | (none) | deliverable `final` or `sent`; docx present | bundle_created |
| `/deliverables/{id}/bundle/verify` | POST | Yes | (none) | n/a | bundle_verified / bundle_verify_failed |
| `/deliverables/{id}/bundles/{bundle_id}/download` | GET | Yes | `deliverable:download_bundle` | deliverable `sent`; bundle not revoked | bundle_downloaded / bundle_download_denied |
| `/deliverables/{id}/bundles/{bundle_id}/revoke` | POST | Yes | (none) | n/a | bundle_revoked |

## Evidence

| Endpoint | Method | Auth | Scope | State | Audit |
|---|---:|---:|---|---|---:|
| `/deliverables/{id}/evidence` | POST | Yes | `deliverable:evidence` | deliverable `sent` | (optional) |
| `/deliverables/{id}/evidence/{evidence_id}/download` | GET | Yes | `deliverable:evidence_download` | deliverable `sent`; evidence not revoked | evidence_downloaded / evidence_download_denied |
| `/deliverables/{id}/evidence/{evidence_id}/revoke` | POST | Yes | (none) | n/a | evidence_revoked |

## Audit / Metrics

| Endpoint | Method | Auth | Scope | Notes |
|---|---:|---:|---|---|
| `/audit` | GET | Yes | (none) | tenant-scoped; hash-chained |
| `/audit/verify-chain` | GET | Yes | (none) | verifies hash chain |
| `/runs/{id}/metrics` | GET | Yes | (none) | metadata only |

## Enforcement expectations

- Missing token: **401**
- Wrong scope: **403**
- Wrong lifecycle state (e.g., not sent): **409**
- Cross-tenant access: **404** (preferred) or **403** depending on endpoint.

This matrix is enforced by integration tests in `tests/test_authz_matrix_enforcement.py`.
