# Add tag and theme write commands

- Status: done
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-write-scope-expansion-decision.md`, `docs/decisions/0001-read-only-bootstrap-scope.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

Superset supports tag and theme write operations such as create, update, delete, favorites, tagging, and theme activation. None of these are currently available in the CLI.

## Definition of done

- [x] The approved tag and theme write surface is defined.
- [x] CLI commands and client helpers implement the approved operations.
- [x] Tests cover success paths, failure handling, and safe user-facing behavior.
- [x] `README.md`, `docs/architecture/README.md`, and any required decision records are updated.

## Notes

Blocked until write-capable scope is explicitly approved.

## Resolution

Closed 2026-06-06 by the write-command rollout: `docs/plans/2026-06-06-write-command-rollout.md`. Scope and safety contract are defined in `docs/decisions/0010-write-scope-expansion.md` (uniform `--allow-write` per invocation, no exceptions). Write commands and their tests live in `src/superset_cli/cli.py`, `src/superset_cli/client.py`, and `tests/test_writes.py`.
