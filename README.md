# superset-cli

CLI for self-hosted Apache Superset.

[MIT licensed](LICENSE). Copyright (c) 2026 Robin Rittsteiger.

## Scope

Current scope (read by default, write opt-in):
- Python project managed with `uv`
- `devenv` shell configured for Python + uv
- local instance config management (add, list, remove)
- browser-cookie import login with immediate live validation + saved auth-state inspection
- read access to dashboards, charts, datasets, databases, annotation layers, CSS templates, themes, tags, reports, saved queries, queries, logs, permalinks, OpenAPI, embedded configs, related objects, chart data
- write access to chart, dashboard, dataset, database, saved-query, SQL Lab, tag, theme, security (roles, users, RLS), and asset-import surfaces; **every write command requires `--allow-write` on every invocation** (see [ADR 0009](docs/decisions/0009-write-command-explicit-opt-in.md) and [ADR 0010](docs/decisions/0010-write-scope-expansion.md))
- shared list-query controls on all list commands via `--page` (0-based), `--page-size`, `--search`, `--order-column`, and `--order-direction`
- user-friendly error messages for auth expiry, missing resources, and network failures (exit code 1, no raw tracebacks)

## Decision log

Long-lived technical reasoning lives in `docs/decisions/`.

Use it to understand why key choices were made, not just what the code does. Start with `docs/decisions/README.md`.

## Documentation map

A top-level map of repository docs lives in `docs/index.md`.
A glossary of repository-specific terms lives in `docs/glossary.md`.

## Architecture

A structural overview of modules, command-to-code mappings, and test entry points lives in `docs/architecture/README.md`.

## Installation for users

After the first PyPI release, install the CLI without cloning this repository:

```bash
uv tool install superset-cli
superset-cli --help
```

Upgrade with `uv tool upgrade superset-cli`. Python 3.12 or newer is required;
uv can provision Python when needed. `pipx install superset-cli` is an alternative.
The release workflow exists, but a published package is not yet confirmed.

## Publishing releases (maintainers)

The canonical upstream is [RobinOnHisOwn/superset_cli](https://github.com/RobinOnHisOwn/superset_cli),
owned by the `RobinOnHisOwn` organization. The company repository is a mirror, not
an independent publishing source.

Before the first release:

1. Confirm ownership and permission to publish from the canonical repository,
   and review source and Git history for sensitive material. MIT licensing is configured
   in `LICENSE` and the distribution metadata.
2. Keep this repository excluded from shared self-hosted runner groups. CI and publishing
   use GitHub-hosted `ubuntu-latest` runners.
3. Create a GitHub environment named `pypi` with required reviewer approval and
   restrict deployment to tags matching `v*` (no branches). A sole maintainer can
   select themselves as reviewer with prevent-self-review disabled. On Free/Pro/Team,
   required reviewers are available only for public repositories; configure this gate
   after making the reviewed repository public, before publishing. Protect release
   tags and `main` against unauthorized changes.
4. Configure a pending [PyPI Trusted Publisher](https://pypi.org/manage/account/publishing/)
   with project `superset-cli`, owner `RobinOnHisOwn`, repository `superset_cli`, workflow filename
   `publish.yml`, and environment `pypi`. Do not create an API-token secret.
   Configure only the canonical repository, not mirrors.

For each release, update `project.version` in `pyproject.toml` and regenerate `uv.lock`
with `uv lock`; have the change reviewed and CI pass. Run **Build and publish** manually
for a build-only rehearsal. Publish a GitHub release from the reviewed commit with a
matching tag (for example `v0.1.0` for version `0.1.0`), then approve the `pypi`
environment deployment. Manual runs never publish; published releases build and test
before publishing the same artifacts. PyPI versions cannot be overwritten: use a new
version for changed distributions. Prereleases also publish, so use a corresponding
version such as `0.2.0rc1` and tag `v0.2.0rc1`.

See [ADR 0011](docs/decisions/0011-pypi-release-publishing.md) for the security rationale.

## Quick start for contributors

If you use `direnv`, allow the repo once and `devenv` will auto-activate whenever you enter this directory.

```bash
direnv allow
uv sync --group dev
uv run superset-cli --help
uv run pytest -v
```

Without `direnv`, enter the shell manually:

```bash
devenv shell
```

## Custom authenticated API calls

```bash
uv run superset-cli api prod /api/v1/_openapi --json
uv run superset-cli api prod /api/v1/dashboard/ --param 'q={"page":0,"page_size":10}' --json
uv run superset-cli api prod /api/v1/chart/42 --method PUT --file /tmp/chart.json --allow-write --json
```

Replace the instance and IDs with discovered values; the write example is not permission to execute it.
GET is the default. POST, PUT, PATCH, and DELETE require `--allow-write`, including read-like POST calls.
Use repeated `--param KEY=VALUE` options and JSON object bodies through `--body`, `--body -` (stdin), or `--file`.
Responses preserve the full API envelope: `--json` emits compact JSON, otherwise pretty JSON.

The command validates the saved session before sending the request. Missing or rejected authentication triggers one browser-cookie import attempt with live validation; select a browser with `--browser zen` if needed.
You must already be signed in in that browser. Recovery progress goes to stderr; no browser is launched and sent mutations are never retried. Network errors and permission failures do not trigger recovery.
Only instance-relative `/api/v1/` paths are accepted and redirects are not followed. Custom requests handle CSRF automatically. Existing commands retain their explicit login behavior.

## Current commands

```bash
uv run superset-cli instances add prod https://superset.example.com
uv run superset-cli instances list --json
uv run superset-cli instances remove prod --json
uv run superset-cli auth login prod                          # auto-detect: chrome -> edge -> brave -> firefox -> zen -> safari
uv run superset-cli auth login prod --browser firefox        # read cookies from Firefox
uv run superset-cli auth login prod --browser zen --json     # read cookies from Zen Browser
uv run superset-cli auth logout prod --json
uv run superset-cli auth status prod --json
uv run superset-cli auth validate prod --json
uv run superset-cli openapi fetch prod --json
uv run superset-cli me show prod --json
uv run superset-cli me roles prod --json
uv run superset-cli dashboards list prod --json
uv run superset-cli dashboards list prod --page 0 --page-size 25 --json
uv run superset-cli dashboards list prod --search Revenue --order-column dashboard_title --order-direction asc --json
uv run superset-cli dashboards get prod 7 --json
uv run superset-cli dashboards diff prod 7 8 --json           # field-by-field record comparison
uv run superset-cli dashboards charts prod 7 --json
uv run superset-cli dashboards datasets prod 7 --json
uv run superset-cli charts list prod --json
uv run superset-cli charts list prod --page 1 --page-size 10 --json
uv run superset-cli charts list prod --search Revenue --order-column slice_name --order-direction desc --json
uv run superset-cli charts get prod 42 --json
uv run superset-cli datasets list prod --json
uv run superset-cli datasets list prod --page 0 --page-size 50 --json
uv run superset-cli datasets list prod --search orders --order-column table_name --order-direction asc --json
uv run superset-cli datasets get prod 5 --json
uv run superset-cli databases list prod --json
uv run superset-cli databases list prod --page 0 --page-size 10 --json
uv run superset-cli databases list prod --search analytics --order-column database_name --order-direction desc --json
uv run superset-cli databases get prod 1 --json
uv run superset-cli databases schemas prod 1 --json
uv run superset-cli databases tables prod 1 --schema analytics --json
uv run superset-cli dashboards embedded prod 7 --json
uv run superset-cli datasets related prod 21 --json
uv run superset-cli charts data prod 10 --json
uv run superset-cli annotation-layers list prod --json
uv run superset-cli annotation-layers get prod 50 --json
uv run superset-cli css-templates list prod --json
uv run superset-cli css-templates get prod 1 --json
uv run superset-cli themes list prod --json
uv run superset-cli themes get prod 1 --json
uv run superset-cli tags list prod --json
uv run superset-cli tags get prod 1 --json
uv run superset-cli reports list prod --json
uv run superset-cli reports get prod 1 --json
uv run superset-cli saved-queries list prod --json
uv run superset-cli saved-queries get prod 1 --json
uv run superset-cli queries list prod --json
uv run superset-cli queries get prod 1 --json
uv run superset-cli logs list prod --json
uv run superset-cli logs get prod 1 --json
uv run superset-cli logs recent-activity prod --json
uv run superset-cli permalinks resolve prod dashboard abc123 --json
uv run superset-cli datasources column-values prod table 21 country --json
```

## Write commands

Every command in the table below requires `--allow-write` on every invocation. Without it the command prints what it *would* do and exits non-zero (dry-run by default).

```bash
# Charts
uv run superset-cli charts create     prod --body '{"slice_name":"Revenue","viz_type":"line"}' --allow-write
uv run superset-cli charts update     prod 42 --body '{"slice_name":"Revenue v2"}' --allow-write
uv run superset-cli charts update     prod 42 --clear-query-context --allow-write   # drop stale saved query_context after a params edit
uv run superset-cli charts delete     prod 42 --allow-write
uv run superset-cli charts favorite   prod 42 --allow-write
uv run superset-cli charts unfavorite prod 42 --allow-write

# Dashboards
uv run superset-cli dashboards create     prod --file dashboard.json --allow-write
uv run superset-cli dashboards update     prod 7  --body '{"published":true}' --allow-write
uv run superset-cli dashboards delete     prod 7  --allow-write
uv run superset-cli dashboards favorite   prod 7  --allow-write
uv run superset-cli dashboards unfavorite prod 7  --allow-write
uv run superset-cli dashboards copy       prod 7  --body '{"dashboard_title":"Revenue (copy)"}' --allow-write

# Datasets
uv run superset-cli datasets create  prod --file dataset.json --allow-write
uv run superset-cli datasets update  prod 21 --body '{"description":"updated"}' --allow-write
uv run superset-cli datasets delete  prod 21 --allow-write
uv run superset-cli datasets refresh prod 21 --allow-write

# Databases
uv run superset-cli databases create          prod --file database.json --allow-write
uv run superset-cli databases update          prod 1 --body '{"expose_in_sqllab":true}' --allow-write
uv run superset-cli databases delete          prod 1 --allow-write
uv run superset-cli databases test-connection prod --file connection.json --allow-write

# Saved queries
uv run superset-cli saved-queries create prod --body '{"label":"q1","sql":"select 1"}' --allow-write
uv run superset-cli saved-queries update prod 9 --body '{"label":"q1-v2"}' --allow-write
uv run superset-cli saved-queries delete prod 9 --allow-write

# SQL Lab
uv run superset-cli sqllab execute    prod --body '{"database_id":1,"sql":"select 1"}' --allow-write
uv run superset-cli sqllab format-sql prod --body '{"sql":"select 1"}' --allow-write
uv run superset-cli sqllab estimate   prod --body '{"database_id":1,"sql":"select 1"}' --allow-write
uv run superset-cli sqllab stop-query prod --body '{"client_id":"abc"}' --allow-write

# Tags, themes
uv run superset-cli tags create   prod --body '{"name":"finance"}' --allow-write
uv run superset-cli tags update   prod 1 --body '{"name":"finance-v2"}' --allow-write
uv run superset-cli tags delete   prod 1 --allow-write
uv run superset-cli themes create prod --body '{"theme_name":"Dark"}' --allow-write
uv run superset-cli themes update prod 1 --body '{"theme_name":"Dark v2"}' --allow-write
uv run superset-cli themes delete prod 1 --allow-write

# Security: roles, users, RLS rules
uv run superset-cli security role-create prod --body '{"name":"Analyst"}' --allow-write
uv run superset-cli security role-update prod 5 --body '{"name":"Analyst v2"}' --allow-write
uv run superset-cli security role-delete prod 5 --allow-write
uv run superset-cli security user-create prod --file user.json --allow-write
uv run superset-cli security user-update prod 2 --body '{"active":false}' --allow-write
uv run superset-cli security user-delete prod 2 --allow-write
uv run superset-cli security rls create  prod --file rls.json --allow-write
uv run superset-cli security rls update  prod 3 --body '{"name":"updated"}' --allow-write
uv run superset-cli security rls delete  prod 3 --allow-write

# Asset import (server-side multipart upload)
uv run superset-cli import upload prod dashboard --file bundle.zip --allow-write
uv run superset-cli import upload prod chart     --file bundle.zip --overwrite --passwords '{"db.zip":"hunter2"}' --allow-write
```

Both `--body '<json>'` and `--file <path-to-json>` accept the request payload. Pass `--body -` to read JSON from stdin. The two flags are mutually exclusive.

## Local Superset for testing

`devenv` includes a process that boots a sqlite-backed Apache Superset on `http://localhost:8088` for ad-hoc CLI testing. No Redis, no Celery, no Docker. First boot installs Superset into `.devenv/state/superset/venv/` and seeds an admin user (~1–2 min). Subsequent boots are seconds.

```bash
devenv up superset                # start it (or: bash scripts/dev-superset.sh)
superset-open                     # open http://localhost:8088/login/ in your default browser
# log in as user: admin   password: admin

superset-cli instances add local http://localhost:8088
superset-cli auth login local     # reads cookies from your installed browser
superset-cli me show local --json
superset-cli tags create local --body '{"name":"smoke"}' --allow-write --json
```

The dev instance disables CSRF and Talisman so cookie auth works without extra setup. It is not safe to expose. State lives under `.devenv/state/superset/`; delete that directory to reset.

### Snowflake connections from `~/.snowflake/connections.toml`

On every Superset start, `scripts/dev-superset-import-snowflake.sh` reconciles the local instance's database list against `~/.snowflake/connections.toml`. Connections missing in Superset are created as `snowflake-<name>`; existing ones are skipped. Auth methods supported:

- **password** — baked into the SQLAlchemy URI.
- **key-pair** (`private_key_path` / `private_key_file`) — mapped to `authenticator=snowflake_jwt`, key path stored in the database's `extra`.
- **PROGRAMMATIC_ACCESS_TOKEN** — the file at `token_file_path` is read and submitted as the password. No `authenticator` parameter is sent (the connector rejects `PROGRAMMATIC_ACCESS_TOKEN` as an authenticator value even though the Snowflake CLI uses that label in TOML).
- **externalbrowser / oauth** — skipped (no browser on the server).

If a TOML entry has no `database` field, the importer defaults to `SNOWFLAKE_SAMPLE_DATA` so Superset's connection-test query has a current database. Failures in the importer never bring down the Superset server. Secrets written into Superset's sqlite metadata DB are protected only by a static dev `SECRET_KEY` — do not point this at a production credential.
