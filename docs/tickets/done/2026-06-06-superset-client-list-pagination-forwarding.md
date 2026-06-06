# Superset client list pagination forwarding

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/client.py`, `tests/test_client.py`, `tests/test_dashboards.py`, `tests/test_charts.py`, `tests/test_datasets.py`, `tests/test_databases.py`

## Context

List-method pagination forwarding is already implemented across `list_dashboards`, `list_charts`, `list_datasets`, and `list_databases`. The client passes page settings through to the Superset list endpoints and the CLI forwards user-provided flags.

## Definition of done

- [x] Each list client method uses `build_list_params` to construct the `q` payload.
- [x] CLI list commands accept `--page` and `--page-size` flags and pass them to the client.
- [x] Tests verify per-command forwarding and stable JSON output shape when pagination flags are present.

## Notes

This is a cross-cutting behavior shared by all current list commands.
