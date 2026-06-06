# Add asset import write commands

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-write-scope-expansion-decision.md`, `docs/tickets/todo/2026-06-06-read-only-export-commands.md`, `docs/decisions/0001-read-only-bootstrap-scope.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

Superset supports import endpoints for dashboards, charts, datasets, databases, saved queries, themes, and bundled assets. None of these server-side write flows are currently available in the CLI.

## Definition of done

- [x] The approved import-capable resource types and file-handling contract are defined.
- [x] CLI commands and client helpers implement the approved import operations.
- [x] Tests cover file handling, failure behavior, and safe user-facing messaging.
- [x] `README.md`, `docs/architecture/README.md`, and any required decision records are updated.

## Notes

Blocked until write-capable scope is explicitly approved.

## Resolution

Closed 2026-06-06 by the write-command rollout: `docs/plans/2026-06-06-write-command-rollout.md`. Scope and safety contract are defined in `docs/decisions/0010-write-scope-expansion.md` (uniform `--allow-write` per invocation, no exceptions). Write commands and their tests live in `src/superset_cli/cli.py`, `src/superset_cli/client.py`, and `tests/test_writes.py`.
