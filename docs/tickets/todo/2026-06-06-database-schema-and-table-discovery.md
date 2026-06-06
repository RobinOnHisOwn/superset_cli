# Add database schema and table discovery commands

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_databases.py`, `tests/test_databases_get.py`, `README.md`, `docs/architecture/README.md`

## Context

`databases list` and `databases get` confirm that a database exists, but they do not expose the read-only metadata discovery endpoints that make the resource useful for agents. Superset provides endpoints for listing schemas and tables, and those should be reachable from the CLI.

## Definition of done

- [ ] Client helpers exist for database schema and table discovery endpoints.
- [ ] CLI commands support listing schemas for a database and listing tables, including any required schema selector.
- [ ] Tests cover param forwarding, output modes, and error handling.
- [ ] `README.md` and `docs/architecture/README.md` document the new commands.

## Notes

Keep this ticket focused on metadata discovery. Do not expand into SQL execution or any write-capable database endpoints.
