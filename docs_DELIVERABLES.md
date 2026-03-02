# Deliverables Layer Notes

## Purpose

Artifacts are immutable and hash-identified. Deliverables are a tenant-scoped pointer layer that lets operators declare:

- what was delivered
- when it was finalized/sent
- what superseded what

Artifacts remain the ground truth; deliverables provide lifecycle semantics.

## Endpoints

- `POST /deliverables`
- `GET /deliverables/{deliverable_id}`
- `POST /deliverables/{deliverable_id}/finalize`
- `POST /deliverables/{deliverable_id}/mark_sent`
- `POST /deliverables/{deliverable_id}/supersede`
- `GET /runs/{pipeline_run_id}/deliverables_list` (list deliverables for run)

All endpoints are tenant-scoped via JWT claim and RLS.
