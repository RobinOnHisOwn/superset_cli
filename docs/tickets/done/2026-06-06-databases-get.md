# Databases get command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_databases_get.py`, `docs/architecture/README.md`

## Context

`databases get <instance> <pk>` is already implemented. It fetches a single database object and formats it for JSON or concise human-readable display.

## Definition of done

- [x] The command rejects unknown instances and missing auth state.
- [x] `--json` returns the unwrapped database object.
- [x] Human output shows database ID, name, and backend while not-found and network errors are surfaced clearly.

## Notes

This command reuses the shared CLI API-error handling context manager.
