# Add database schema and table discovery commands

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_databases.py`, `tests/test_databases_get.py`, `README.md`, `docs/architecture/README.md`

## Context

`databases list` and `databases get` confirm that a database exists, but they do not expose the read-only metadata discovery endpoints that make the resource useful for agents. Superset provides endpoints for listing schemas and tables, and those should be reachable from the CLI.

## Definition of done

- [x] Client helpers exist for database schema and table discovery endpoints.
- [x] CLI commands support listing schemas for a database and listing tables, including any required schema selector.
- [x] Tests cover param forwarding, output modes, and error handling.
- [x] `README.md` and `docs/architecture/README.md` document the new commands.

## Notes

Keep this ticket focused on metadata discovery. Do not expand into SQL execution or any write-capable database endpoints.
