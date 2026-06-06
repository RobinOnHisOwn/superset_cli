# Add asset import write commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-write-scope-expansion-decision.md`, `docs/tickets/todo/2026-06-06-read-only-export-commands.md`, `docs/decisions/0001-read-only-bootstrap-scope.md`, `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`

## Context

Superset supports import endpoints for dashboards, charts, datasets, databases, saved queries, themes, and bundled assets. None of these server-side write flows are currently available in the CLI.

## Definition of done

- [ ] The approved import-capable resource types and file-handling contract are defined.
- [ ] CLI commands and client helpers implement the approved import operations.
- [ ] Tests cover file handling, failure behavior, and safe user-facing messaging.
- [ ] `README.md`, `docs/architecture/README.md`, and any required decision records are updated.

## Notes

Blocked until write-capable scope is explicitly approved.
