import os
import psycopg
from datetime import datetime, timedelta, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dadi:dadi@localhost:5432/dadi")

BUNDLE_RETENTION_DAYS = int(os.getenv("DADI_BUNDLE_RETENTION_DAYS", "30"))
EVIDENCE_RETENTION_DAYS = int(os.getenv("DADI_EVIDENCE_RETENTION_DAYS", "90"))

def main():
    now = datetime.now(timezone.utc)
    bundle_cutoff = now - timedelta(days=BUNDLE_RETENTION_DAYS)
    evidence_cutoff = now - timedelta(days=EVIDENCE_RETENTION_DAYS)

    with psycopg.connect(DATABASE_URL) as c:
        with c.transaction():
            c.execute(
                "UPDATE deliverable_bundles SET status='revoked', revoked_at=now() "
                "WHERE status='created' AND created_at < %s",
                (bundle_cutoff,),
            )
            c.execute(
                "UPDATE deliverable_evidence SET status='revoked', revoked_at=now() "
                "WHERE status='created' AND created_at < %s",
                (evidence_cutoff,),
            )
    print("Retention sweep complete.")

if __name__ == "__main__":
    main()
