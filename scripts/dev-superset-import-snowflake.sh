#!/usr/bin/env bash
# Reconcile the local dev Superset's database connections against
# ~/.snowflake/connections.toml. Idempotent: connections that already
# exist (matched by database_name) are skipped. Designed to be re-run
# on every Superset start.
#
# Auth handling:
#   - password                          -> baked into the sqlalchemy_uri
#   - private_key_path/_file            -> authenticator=snowflake_jwt; key
#                                          path stored in the database's `extra`
#   - PROGRAMMATIC_ACCESS_TOKEN + token_file_path
#                                       -> token read from disk and used as the
#                                          plain password. NOTE: do not pass
#                                          authenticator=PROGRAMMATIC_ACCESS_TOKEN
#                                          to snowflake-connector-python — the
#                                          server rejects it. Snowflake CLI's
#                                          TOML field is a hint for the CLI,
#                                          not a parameter the connector takes.
#   - externalbrowser/oauth             -> skipped (no browser on the server)
#
# Secrets caveat: this writes connection passwords/keys into the dev
# Superset metadata sqlite at .devenv/state/superset/home/superset.db.
# That file is gitignored, but the SECRET_KEY used to encrypt it is a
# static dev placeholder. Do not point this at a production secret you
# care about — it's for local testing.
set -euo pipefail

ROOT="${DEVENV_ROOT:-$(pwd)}"
VENV="$ROOT/.devenv/state/superset/venv"
PORT="${SUPERSET_PORT:-8088}"
SUPERSET_URL="http://localhost:$PORT"
TOML_PATH="${SNOWFLAKE_CONNECTIONS:-$HOME/.snowflake/connections.toml}"

if [[ ! -f "$TOML_PATH" ]]; then
  echo "[snowflake-import] $TOML_PATH not found — nothing to do"
  exit 0
fi

# Wait for Superset to be reachable (it may have just started)
code="000"
for _ in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$SUPERSET_URL/health" 2>/dev/null || echo "000")
  [[ "$code" == "200" ]] && break
  sleep 1
done
if [[ "$code" != "200" ]]; then
  echo "[snowflake-import] Superset not reachable at $SUPERSET_URL — giving up"
  exit 1
fi

# Lazy-install the Snowflake dialect into the sidecar venv on first use.
if [[ ! -d "$VENV/lib/python3.11/site-packages/snowflake/sqlalchemy" ]]; then
  echo "[snowflake-import] installing snowflake-sqlalchemy into the sidecar venv (one-time, ~30s)..."
  uv pip install --python "$VENV/bin/python" 'snowflake-sqlalchemy>=1.5' >/dev/null
fi

"$VENV/bin/python" - "$TOML_PATH" "$SUPERSET_URL" << 'PY'
import json
import os
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar

toml_path, base_url = sys.argv[1], sys.argv[2]

with open(toml_path, "rb") as fh:
    raw = tomllib.load(fh)

# Snowflake CLI supports two layouts:
#   1) top-level tables are connections
#   2) nested under [connections.<name>]
if "connections" in raw and isinstance(raw["connections"], dict):
    connections = raw["connections"]
else:
    connections = {k: v for k, v in raw.items() if isinstance(v, dict)}

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.open(f"{base_url}/login/")
opener.open(
    f"{base_url}/login/",
    urllib.parse.urlencode({"username": "admin", "password": "admin"}).encode(),
)

def get_json(path: str) -> dict:
    with opener.open(f"{base_url}{path}") as r:
        return json.load(r)

def post_json(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req) as r:
        return json.load(r)

existing_names = {d["database_name"] for d in get_json("/api/v1/database/").get("result", [])}

created = skipped = failed = 0

for name, conn in connections.items():
    db_name = f"snowflake-{name}"

    if db_name in existing_names:
        print(f"[snowflake-import] {db_name} already present — skipping")
        skipped += 1
        continue

    authenticator = (conn.get("authenticator") or "").lower()
    if authenticator in {"externalbrowser", "oauth"}:
        print(f"[snowflake-import] {name}: authenticator={authenticator} not supported headless — skipping")
        skipped += 1
        continue

    user = conn.get("user") or conn.get("username")
    account = conn.get("account") or conn.get("accountname")
    if not user or not account:
        print(f"[snowflake-import] {name}: missing user/account — skipping")
        skipped += 1
        continue

    password = conn.get("password")
    private_key_path = conn.get("private_key_path") or conn.get("private_key_file")
    token_file_path = conn.get("token_file_path")

    # PROGRAMMATIC_ACCESS_TOKEN: read the token file and use it as the password.
    if authenticator == "programmatic_access_token" and token_file_path and not password:
        try:
            password = open(os.path.expanduser(token_file_path)).read().strip()
        except OSError as exc:
            print(f"[snowflake-import] {name}: cannot read token_file_path {token_file_path}: {exc} — skipping")
            skipped += 1
            continue

    if not password and not private_key_path:
        print(f"[snowflake-import] {name}: no password / private_key_path / readable token_file_path — skipping")
        skipped += 1
        continue

    database = conn.get("database")
    schema = conn.get("schema", "")
    if not database:
        # Superset's connection-test runs a query that needs a current database
        # in the session. Default to SNOWFLAKE_SAMPLE_DATA, the read-only sample
        # DB that ships with every Snowflake account.
        database = "SNOWFLAKE_SAMPLE_DATA"
        print(f"[snowflake-import] {name}: no database set in TOML — defaulting to {database}")
    warehouse = conn.get("warehouse")
    role = conn.get("role")

    if password:
        userinfo = f"{urllib.parse.quote(user, safe='')}:{urllib.parse.quote(password, safe='')}"
    else:
        userinfo = urllib.parse.quote(user, safe="")

    path_tail = "/".join(p for p in (database, schema) if p)

    params: dict[str, str] = {}
    if warehouse: params["warehouse"] = warehouse
    if role:      params["role"] = role
    if private_key_path:
        params["authenticator"] = "snowflake_jwt"
    # PAT: do not pass an authenticator; the connector rejects it.
    qstr = ("?" + urllib.parse.urlencode(params)) if params else ""

    uri = f"snowflake://{userinfo}@{account}/{path_tail}{qstr}"

    extra: dict = {}
    if private_key_path:
        extra["engine_params"] = {
            "connect_args": {"private_key_file": os.path.expanduser(private_key_path)}
        }

    body: dict = {
        "database_name": db_name,
        "engine": "snowflake",
        "sqlalchemy_uri": uri,
    }
    if extra:
        body["extra"] = json.dumps(extra)

    try:
        post_json("/api/v1/database/", body)
        print(f"[snowflake-import] created {db_name}")
        created += 1
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="ignore")[:300]
        print(f"[snowflake-import] FAILED {db_name}: HTTP {e.code} {msg}")
        failed += 1

print(f"[snowflake-import] summary: {created} created, {skipped} skipped, {failed} failed")
PY
