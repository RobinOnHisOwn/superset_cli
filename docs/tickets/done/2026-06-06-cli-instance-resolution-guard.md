# CLI instance resolution guard

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/config.py`, `tests/test_auth.py`, `tests/test_auth_validate.py`, `tests/test_dashboards.py`, `tests/test_charts.py`, `tests/test_datasets.py`, `tests/test_databases.py`

## Context

The CLI already centralizes known-instance checks through `_require_instance`. Commands that need an instance fail early with a consistent error if the instance name is unknown.

## Definition of done

- [x] `_require_instance` loads config and looks up the named instance.
- [x] Unknown instances produce a consistent `Unknown instance` error message and exit code 1.
- [x] Commands across auth and resource groups reuse the same guard behavior.

## Notes

This helper keeps command precondition behavior consistent.
