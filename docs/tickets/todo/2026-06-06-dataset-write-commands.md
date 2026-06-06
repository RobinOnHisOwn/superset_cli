# Add dataset write commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-write-scope-expansion-decision.md`, `docs/decisions/0001-read-only-bootstrap-scope.md`, `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`

## Context

Superset supports dataset write operations such as create, update, delete, duplicate, refresh, and metric or column changes. None of these are currently available in the CLI.

## Definition of done

- [ ] The approved dataset write surface is defined.
- [ ] CLI commands and client helpers implement the approved dataset write operations.
- [ ] Tests cover success paths, failure handling, and safe user-facing behavior.
- [ ] `README.md`, `docs/architecture/README.md`, and any required decision records are updated.

## Notes

Blocked until write-capable scope is explicitly approved.
