#!/usr/bin/env bash
# Boot a local Apache Superset for ad-hoc testing of the CLI.
# Idempotent: first run installs into a sidecar venv and seeds an admin user;
# subsequent runs just start the server.
#
# Resulting instance:
#   URL:      http://localhost:${SUPERSET_PORT:-8088}
#   Login:    admin / admin
#   Metadata: sqlite at $DEVENV_ROOT/.devenv/state/superset/home/superset.db
#
# Not for production. The dev config disables CSRF and Talisman so the
# CLI's cookie-based auth works against a freshly seeded box without
# extra setup.
set -euo pipefail

ROOT="${DEVENV_ROOT:-$(pwd)}"
SUPERSET_DIR="$ROOT/.devenv/state/superset"
VENV="$SUPERSET_DIR/venv"
export SUPERSET_HOME="$SUPERSET_DIR/home"
export FLASK_APP=superset
export SUPERSET_CONFIG_PATH="$SUPERSET_HOME/superset_config.py"
export PYTHONPATH="$SUPERSET_HOME"
PORT="${SUPERSET_PORT:-8088}"

mkdir -p "$SUPERSET_HOME"

if [[ ! -x "$VENV/bin/superset" ]]; then
  echo "[dev-superset] first-time install into $VENV (~1-2 min)..."
  uv venv --python 3.11 "$VENV"
  # cachetools is a missing transitive dep of apache-superset's aws_iam engine spec
  uv pip install --python "$VENV/bin/python" apache-superset cachetools
fi

if [[ ! -f "$SUPERSET_CONFIG_PATH" ]]; then
  cat > "$SUPERSET_CONFIG_PATH" << 'PYCFG'
import os

SECRET_KEY = "dev-only-secret-not-for-prod-7f3a8c9b2e1d5f4a"
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.environ['SUPERSET_HOME']}/superset.db"
WTF_CSRF_ENABLED = False
TALISMAN_ENABLED = False
FEATURE_FLAGS = {"ALERT_REPORTS": False}
PYCFG
fi

if [[ ! -f "$SUPERSET_HOME/.initialized" ]]; then
  echo "[dev-superset] initializing sqlite metadata DB and admin user..."
  "$VENV/bin/superset" db upgrade
  "$VENV/bin/superset" fab create-admin \
    --username admin --firstname Admin --lastname User \
    --email admin@example.com --password admin
  "$VENV/bin/superset" init
  touch "$SUPERSET_HOME/.initialized"
fi

echo "[dev-superset] ready: http://localhost:$PORT  (admin/admin)"

# Start the server in the background so we can run post-start hooks.
"$VENV/bin/superset" run -p "$PORT" --host 0.0.0.0 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT INT TERM

# Best-effort: reconcile Snowflake connections from ~/.snowflake/connections.toml.
# Failure here must not bring down the server.
( bash "$ROOT/scripts/dev-superset-import-snowflake.sh" || true ) &

wait "$SERVER_PID"
