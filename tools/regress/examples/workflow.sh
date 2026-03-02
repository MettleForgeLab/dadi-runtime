# Example workflow

export DATABASE_URL="postgresql://user:pass@localhost:5432/dadi"

# Record a fixture from a pipeline run
python -m dadi_regress.cli record --pipeline-run-id 00000000-0000-0000-0000-000000000000 --out fixture_000.zip

# Verify hashes
python -m dadi_regress.cli verify --fixture fixture_000.zip

# Verify with schemas (point to your schemas directory)
python -m dadi_regress.cli verify --fixture fixture_000.zip --schemas ./schemas

# Diff two fixtures
python -m dadi_regress.cli diff --a fixture_old.zip --b fixture_new.zip
