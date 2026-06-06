# Databases list command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_databases.py`, `docs/architecture/README.md`

## Context

`databases list <instance>` is already implemented. It reads Superset database listings, supports pagination flags, and offers human-readable and JSON output modes.

## Definition of done

- [x] The command rejects unknown instances and missing auth state.
- [x] `--json` returns the full list envelope unchanged, including with pagination flags.
- [x] Human output renders database IDs, names, and backends or `No databases found.` when empty.

## Notes

Tests also verify network-error handling, client closure, and page/page-size forwarding.
