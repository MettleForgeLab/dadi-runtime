# Start gateway
export DATABASE_URL="postgresql://user:pass@localhost:5432/dadi"
psql "$DATABASE_URL" -f sql/schema.sql
psql "$DATABASE_URL" -f sql/regeneration_plans.sql
uvicorn dadi_gateway.app:app --reload --port 8000

# Health
curl http://localhost:8000/health

# Lookup artifact metadata
curl http://localhost:8000/artifacts/<sha256>

# Lookup plan
curl http://localhost:8000/plan/<plan_id>
curl http://localhost:8000/plan/<plan_id>/explain
