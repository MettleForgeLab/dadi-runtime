# DADI Artifact Browser + Diff UI (Minimal)

A minimal Next.js (React) UI for operator-facing inspection of:

- Artifacts (metadata + content preview when JSON)
- Lineage (upstream/downstream edges)
- Regeneration plans (plan + explain)
- JSON diff (two JSON artifacts)

## Configure API base URL

Set `NEXT_PUBLIC_API_BASE` to your gateway URL that fronts the services:

- Artifact Store:
  - `GET /artifacts/{sha256}`
  - `GET /artifacts/{sha256}/content`
  - `GET /lineage/{sha256}/upstream`
  - `GET /lineage/{sha256}/downstream`
- Regeneration Planner:
  - `GET /plan/{plan_id}`
  - `GET /plan/{plan_id}/explain`

Example:

```bash
export NEXT_PUBLIC_API_BASE="http://localhost:8000"
npm install
npm run dev
```

If you run services on different ports, place a thin gateway or reverse proxy in front of them
(or modify `app/lib/api.ts` to route per-service).

## Notes

- This UI intentionally avoids complex styling.
- Diff is structural for JSON objects; binary artifacts are shown as non-JSON.
