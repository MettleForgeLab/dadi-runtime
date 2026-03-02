#!/usr/bin/env sh
set -eu

RELEASE_DIR=""
OUT="audit_report.json"
ALLOW_REVOKED="false"

# parse args
while [ "$#" -gt 0 ]; do
  case "$1" in
    --release-dir) RELEASE_DIR="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --allow-revoked) ALLOW_REVOKED="true"; shift 1;;
    -h|--help)
      echo "Usage: ./run.sh --release-dir <path> [--out audit_report.json] [--allow-revoked]"
      exit 0
      ;;
    *) echo "Unknown arg: $1"; exit 2;;
  esac
done

if [ -z "$RELEASE_DIR" ]; then
  echo "Missing --release-dir"
  exit 2
fi

# create venv
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate

python -m pip install --upgrade pip >/dev/null

# Install pinned deps (hashes not enforced in this bundle)
if [ -f requirements.lock.txt ]; then
  pip install -r requirements.lock.txt >/dev/null
else
  pip install -r requirements.txt >/dev/null
fi

ARGS="--release-dir $RELEASE_DIR --out $OUT"
if [ "$ALLOW_REVOKED" = "true" ]; then
  ARGS="$ARGS --allow-revoked"
fi

python audit_verify.py $ARGS
