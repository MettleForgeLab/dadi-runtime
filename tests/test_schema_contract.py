
import os

def test_schema_contract_best_effort():
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    import psycopg
    with psycopg.connect(url) as c:
        with c.cursor() as cur:
            cur.execute("SELECT to_regclass('public.audit_events')")
            assert cur.fetchone()[0] is not None
            cur.execute("SELECT to_regclass('public.deliverable_bundles')")
            assert cur.fetchone()[0] is not None
            cur.execute("SELECT to_regclass('public.deliverable_evidence')")
            assert cur.fetchone()[0] is not None
            cur.execute("SELECT to_regclass('public.signing_public_keys')")
            assert cur.fetchone()[0] is not None
            cur.execute("SELECT to_regclass('public.idempotency_keys')")
            assert cur.fetchone()[0] is not None

            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='audit_events'")
            cols = {r[0] for r in cur.fetchall()}
            assert 'prev_event_hash' in cols and 'event_hash' in cols

            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='deliverable_bundles'")
            cols = {r[0] for r in cur.fetchall()}
            assert 'status' in cols and 'revoked_at' in cols

            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='deliverable_evidence'")
            cols = {r[0] for r in cur.fetchall()}
            assert 'status' in cols and 'revoked_at' in cols
