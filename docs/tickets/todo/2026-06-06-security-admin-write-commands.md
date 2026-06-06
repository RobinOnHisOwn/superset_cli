# Add security and admin write commands

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-write-scope-expansion-decision.md`, `docs/tickets/todo/2026-06-06-security-read-surface-design.md`, `docs/decisions/0001-read-only-bootstrap-scope.md`, `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`

## Context

Superset exposes write-capable administration endpoints for areas such as roles, users, groups, permissions on resources, row-level security, and report schedules. None of these are currently available in the CLI.

## Definition of done

- [ ] The approved security/admin write surface is defined.
- [ ] CLI commands and client helpers implement the approved operations.
- [ ] Tests cover success paths, failure handling, and safe user-facing behavior.
- [ ] `README.md`, `docs/architecture/README.md`, and any required decision records are updated.

## Notes

Blocked until write-capable scope is explicitly approved. This surface is especially sensitive and may need additional guardrails beyond other write features.
