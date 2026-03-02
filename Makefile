.PHONY: up down seed plan regress verify export-safe clean

# Default environment file (optional)
-include .env

COMPOSE=docker compose
PYTHON=python3

up:
	$(COMPOSE) -f deploy/reference/docker-compose.yml up --build -d

down:
	$(COMPOSE) -f deploy/reference/docker-compose.yml down

seed:
	pip install psycopg[binary] requests >/dev/null 2>&1 || true
	API_BASE=http://localhost:8000 DATABASE_URL=$(DATABASE_URL) $(PYTHON) deploy/reference/scripts/seed_demo.py

plan:
	@echo "Example: make plan OLD=<old_sha> NEW=<new_sha>"
	@if [ -z "$(OLD)" ] || [ -z "$(NEW)" ]; then echo "Set OLD and NEW prompt SHA256s"; exit 1; fi
	curl -s -X POST http://localhost:8000/plan/regenerate \
		-H "Content-Type: application/json" \
		-d '{"old_prompt_sha256":"$(OLD)","new_prompt_sha256":"$(NEW)"}' | jq

regress:
	@echo "Example: make regress RUN=<pipeline_run_id> OUT=fixture.zip"
	@if [ -z "$(RUN)" ] || [ -z "$(OUT)" ]; then echo "Set RUN and OUT"; exit 1; fi
	cd tools/regress && $(PYTHON) -m dadi_regress.cli record --pipeline-run-id $(RUN) --out ../../$(OUT)

verify:
	@echo "Example: make verify FIXTURE=fixture.zip"
	@if [ -z "$(FIXTURE)" ]; then echo "Set FIXTURE"; exit 1; fi
	cd tools/regress && $(PYTHON) -m dadi_regress.cli verify --fixture ../../$(FIXTURE)

export-safe:
	@echo "Example: make export-safe FIXTURE=fixture.zip OUT=safe.zip"
	@if [ -z "$(FIXTURE)" ] || [ -z "$(OUT)" ]; then echo "Set FIXTURE and OUT"; exit 1; fi
	$(PYTHON) posture/confidentiality-security/scripts/safe_fixture_export.py --fixture $(FIXTURE) --out $(OUT)

clean:
	rm -rf *.zip


bundle-verify:
	@echo "Example: make bundle-verify BUNDLE=<bundle_sha> OUT=report.json"
	@if [ -z "$(BUNDLE)" ] || [ -z "$(OUT)" ]; then echo "Set BUNDLE and OUT"; exit 1; fi
	python tools/bundle-verify/bundle_verify.py --bundle-sha $(BUNDLE) --out $(OUT)


# --- Compliance dev loop ---
compliance-up:
	docker compose -f deploy/reference/docker-compose.yml up --build -d

compliance-down:
	docker compose -f deploy/reference/docker-compose.yml down

token:
	@echo "Mint token via local IdP stub"
	@if [ -z "$(TENANT)" ] || [ -z "$(SCOPE)" ]; then echo "Set TENANT and SCOPE"; exit 1; fi
	IDP_URL=http://localhost:9000 python services/idp_stub/scripts/get_token.py --tenant $(TENANT) --scope "$(SCOPE)"

compliance-seed:
	API_BASE=http://localhost:8000 IDP_URL=http://localhost:9000 python deploy/reference/scripts/seed_demo.py

compliance-smoke:
	API_BASE=http://localhost:8000 IDP_URL=http://localhost:9000 python scripts/compliance_smoke.py



# --- Production profile (template) ---
prod-up:
	docker compose -f deploy/reference/docker-compose.prod.yml up --build -d

prod-down:
	docker compose -f deploy/reference/docker-compose.prod.yml down

prod-config-check:
	@echo "Checking required prod env vars..."
	@if [ -z "$$DADI_OIDC_ISSUER" ] || [ -z "$$DADI_OIDC_AUDIENCE" ] || [ -z "$$DADI_OIDC_JWKS_URL" ]; then echo "Missing OIDC env vars"; exit 1; fi
	@if [ -z "$$AWS_REGION" ] || [ -z "$$AWS_KMS_KEY_ID" ] || [ -z "$$DADI_SIGNING_KID" ]; then echo "Missing AWS KMS signing env vars"; exit 1; fi
	@echo "OK"


compliance-gate:
	NEXT_PUBLIC_API_BASE=http://localhost:8000 python scripts/compliance_gate.py


migrate:
	DATABASE_URL=$${DATABASE_URL:-postgresql://dadi:dadi@localhost:5432/dadi} alembic upgrade head

schema-check:
	DATABASE_URL=$${DATABASE_URL:-postgresql://dadi:dadi@localhost:5432/dadi} python -c "from services.gateway.dadi_gateway.schema_check import schema_startup_check; schema_startup_check()"


regen-checksums:
	python - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('.').resolve()
sql_root = root/'services'/'gateway'/'sql'
order = [
    'schema.sql','tenant_isolation_migration.sql','enable_rls.sql','regeneration_plans.sql',
    'deliverables.sql','deliverables_record_migration.sql','deliverable_bundles.sql','deliverable_evidence.sql',
    'audit_events.sql','audit_hash_chain.sql','signing_public_keys.sql','idempotency.sql','revocation.sql'
]
checks = {}
for name in order:
    p = sql_root/name
    checks[name] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
out = root/'services'/'gateway'/'migrations'/'checksums.json'
out.write_text(json.dumps(checks, indent=2, sort_keys=True)+'\n', encoding='utf-8')
print('Wrote', out)
PY


bootstrap:
	docker compose -f deploy/reference/docker-compose.yml up --build -d
	make compliance-gate
	make compliance-smoke
	@echo "Bootstrap complete. See evidence/ for outputs." 
