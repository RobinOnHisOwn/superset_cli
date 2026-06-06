# superset-agent-cli

Agent-friendly CLI for self-hosted Apache Superset.

## Scope

Current bootstrap scope:
- Python project managed with `uv`
- `devenv` shell configured for Python + uv
- read-only CLI skeleton
- local instance config management (add, list, remove)
- Playwright-based browser login scaffold
- saved auth-state inspection and API validation
- read-only dashboard/chart/dataset/database access via Superset REST API
- pagination and page-size controls on all list commands via `--page` (0-based) and `--page-size`
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
uv run playwright install chromium
uv run superset-agent --help
uv run pytest -v
```

Without `direnv`, enter the shell manually:

```bash
devenv shell
```

## Current commands

```bash
uv run superset-agent instances add prod https://superset.example.com
uv run superset-agent instances list --json
uv run superset-agent instances remove prod --json
uv run superset-agent auth login prod
uv run superset-agent auth logout prod --json
uv run superset-agent auth status prod --json
uv run superset-agent auth validate prod --json
uv run superset-agent dashboards list prod --json
uv run superset-agent dashboards list prod --page 0 --page-size 25 --json
uv run superset-agent dashboards get prod 7 --json
uv run superset-agent charts list prod --json
uv run superset-agent charts list prod --page 1 --page-size 10 --json
uv run superset-agent charts get prod 42 --json
uv run superset-agent datasets list prod --json
uv run superset-agent datasets list prod --page 0 --page-size 50 --json
uv run superset-agent datasets get prod 5 --json
uv run superset-agent databases list prod --json
uv run superset-agent databases list prod --page 0 --page-size 10 --json
uv run superset-agent databases get prod 1 --json
```
