# Datasets list command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_datasets.py`, `docs/architecture/README.md`

## Context

`datasets list <instance>` is already implemented. It reads Superset dataset listings, supports pagination flags, and offers human-readable and JSON output modes.

## Definition of done

- [x] The command rejects unknown instances and missing auth state.
- [x] `--json` returns the full list envelope unchanged, including with pagination flags.
- [x] Human output renders dataset IDs, table names, and schema values or `No datasets found.` when empty.

## Notes

Tests also verify network-error handling, client closure, and page/page-size forwarding.
