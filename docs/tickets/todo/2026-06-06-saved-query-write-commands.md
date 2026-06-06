# Add saved-query write commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-write-scope-expansion-decision.md`, `docs/decisions/0001-read-only-bootstrap-scope.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

Superset supports saved-query write operations such as create, update, and delete. None of these are currently available in the CLI.

## Definition of done

- [ ] The approved saved-query write surface is defined.
- [ ] CLI commands and client helpers implement the approved saved-query write operations.
- [ ] Tests cover success paths, failure handling, and safe user-facing behavior.
- [ ] `README.md`, `docs/architecture/README.md`, and any required decision records are updated.

## Notes

Blocked until write-capable scope is explicitly approved.
