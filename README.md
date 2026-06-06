# superset-cli

CLI for self-hosted Apache Superset.

## Scope

Current bootstrap scope:
- Python project managed with `uv`
- `devenv` shell configured for Python + uv
- read-only CLI skeleton
- local instance config management (add, list, remove)
- Playwright-based browser login scaffold
- saved auth-state inspection and API validation
- read-only dashboard/chart/dataset/database access via Superset REST API, including dashboard-related charts/datasets, database schema/table discovery, and live OpenAPI spec fetches
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

## Quick start

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
