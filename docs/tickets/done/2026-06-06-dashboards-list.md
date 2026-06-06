# Dashboards list command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_dashboards.py`, `docs/architecture/README.md`

## Context

`dashboards list <instance>` is already implemented. It requires saved auth state, fetches the Superset dashboard list, supports pagination flags, and renders human or JSON output.

## Definition of done

- [x] The command rejects unknown instances and missing auth state.
- [x] `--json` returns the full list envelope unchanged, including with pagination flags.
- [x] Human output renders dashboard IDs, titles, and published state or `No dashboards found.` when empty.

## Notes

Tests also verify network-error handling, client closure, and page/page-size forwarding.
