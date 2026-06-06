# Datasets get command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_datasets_get.py`, `docs/architecture/README.md`

## Context

`datasets get <instance> <id_or_uuid>` is already implemented. It fetches a single dataset object and formats it for JSON or concise human-readable display.

## Definition of done

- [x] The command rejects unknown instances and missing auth state.
- [x] `--json` returns the unwrapped dataset object.
- [x] Human output shows dataset ID, table name, and schema while not-found and network errors are surfaced clearly.

## Notes

This command reuses the shared CLI API-error handling context manager.
