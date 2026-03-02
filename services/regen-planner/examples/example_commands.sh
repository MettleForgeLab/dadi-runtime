# Example: plan regeneration for a prompt change

export DATABASE_URL="postgresql://user:pass@localhost:5432/dadi"

python -m dadi_regen.cli plan \
  --old-prompt-sha 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef \
  --new-prompt-sha fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
