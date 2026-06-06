# Add security and admin write commands

- Status: done
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-write-scope-expansion-decision.md`, `docs/tickets/todo/2026-06-06-security-read-surface-design.md`, `docs/decisions/0001-read-only-bootstrap-scope.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

Superset exposes write-capable administration endpoints for areas such as roles, users, groups, permissions on resources, row-level security, and report schedules. None of these are currently available in the CLI.

## Definition of done

- [x] The approved security/admin write surface is defined.
- [x] CLI commands and client helpers implement the approved operations.
- [x] Tests cover success paths, failure handling, and safe user-facing behavior.
- [x] `README.md`, `docs/architecture/README.md`, and any required decision records are updated.

## Notes

Blocked until write-capable scope is explicitly approved. This surface is especially sensitive and may need additional guardrails beyond other write features.

## Resolution

Closed 2026-06-06 by the write-command rollout: `docs/plans/2026-06-06-write-command-rollout.md`. Scope and safety contract are defined in `docs/decisions/0010-write-scope-expansion.md` (uniform `--allow-write` per invocation, no exceptions). Write commands and their tests live in `src/superset_cli/cli.py`, `src/superset_cli/client.py`, and `tests/test_writes.py`.
