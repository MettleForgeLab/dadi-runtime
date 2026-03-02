#!/usr/bin/env sh
set -eu

echo "Running golden-path demo (delegates to compliance smoke)..."
make compliance-smoke

echo "Golden-path demo complete."
echo "See evidence/ for outputs."
