# Dashboards get command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_dashboards_get.py`, `docs/architecture/README.md`

## Context

`dashboards get <instance> <id_or_slug>` is already implemented. It fetches a single dashboard resource and renders either the raw JSON object or selected human-readable fields.

## Definition of done

- [x] The command rejects unknown instances and missing auth state.
- [x] `--json` returns the unwrapped dashboard object.
- [x] Human output shows dashboard ID, title, slug, and published state while not-found and network errors are surfaced clearly.

## Notes

The underlying client normalizes the Superset `{"result": ...}` wrapper.
