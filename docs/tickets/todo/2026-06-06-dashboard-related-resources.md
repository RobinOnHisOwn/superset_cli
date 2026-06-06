# Add dashboard related-resource commands

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_dashboards.py`, `tests/test_dashboards_get.py`, `README.md`, `docs/architecture/README.md`

## Context

The CLI can list dashboards and fetch dashboard details, but it cannot traverse the most useful dashboard relationships. Superset exposes read-only endpoints for a dashboard's charts and datasets, and those are natural agent workflows when moving from a dashboard to the assets behind it.

## Definition of done

- [ ] Client helpers exist for `/api/v1/dashboard/{id_or_slug}/charts` and `/api/v1/dashboard/{id_or_slug}/datasets`.
- [ ] CLI commands expose both related-resource reads with unknown-instance and missing-auth guards.
- [ ] Tests cover JSON output, human output, and 404/auth error handling.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Prefer command names that stay consistent with the existing command tree, for example subcommands under `dashboards` rather than a new top-level group.
