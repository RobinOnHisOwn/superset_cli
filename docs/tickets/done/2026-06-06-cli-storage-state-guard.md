# CLI storage-state guard

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/auth.py`, `tests/test_auth_status.py`, `tests/test_auth_validate.py`, `tests/test_dashboards.py`, `tests/test_charts.py`, `tests/test_datasets.py`, `tests/test_databases.py`

## Context

The CLI already centralizes saved-session checks through `_require_storage_state`. Commands that depend on a saved browser session fail early with a consistent message if the storage-state file is missing.

## Definition of done

- [x] `_require_storage_state` derives the instance storage-state path.
- [x] Missing storage-state files produce a consistent `Run 'auth login' first.` error and exit code 1.
- [x] Commands across auth validation and resource reads reuse the same guard behavior.

## Notes

This helper prevents network calls before local session prerequisites exist.
