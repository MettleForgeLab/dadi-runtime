# Bundle Download Policy (Sent-only)

## Rationale

Compliance environments typically require a clear separation between:
- internal artifact inspection (engineering/debug)
- export of a delivered package (regulated release action)

This pack enforces:
- only *sent* deliverables can be exported as bundles
- export requires a dedicated scope

## Endpoint

`GET /deliverables/{deliverable_id}/bundles/{bundle_id}/download`

Checks:
- tenant context established (JWT/OIDC middleware)
- scope includes `deliverable:download_bundle`
- deliverable exists and status == `sent`
- bundle exists and belongs to deliverable
- returns bundle zip bytes

## Notes

This policy can be extended to require:
- dual control (two-person approval)
- signed download receipts
- immutable sent timestamp
