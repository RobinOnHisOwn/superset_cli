# Add saved query read commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

The current read-only surface covers dashboards, charts, datasets, and databases, but not saved SQL queries. Superset exposes saved-query list and detail endpoints, and they fit the repository's read-only scope.

## Definition of done

- [ ] A new CLI resource group exposes saved-query list and detail reads.
- [ ] Client helpers wrap the corresponding Superset saved-query endpoints.
- [ ] Tests cover human output, JSON output, and guard behavior.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Preserve the current CLI pattern of resource-scoped `list` and `get` commands unless a stronger repository-wide pattern emerges.
