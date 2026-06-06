# CLI API error mapping context manager

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_auth_validate.py`, `tests/test_dashboards_get.py`, `tests/test_charts_get.py`, `tests/test_datasets_get.py`, `tests/test_databases_get.py`

## Context

The CLI already wraps Superset API calls in `_api_errors()`. This context manager converts client exceptions into concise user-facing messages and a non-zero exit code.

## Definition of done

- [x] `AuthExpiredError` is echoed and converted to exit code 1.
- [x] `NotFoundError` is echoed and converted to exit code 1.
- [x] `httpx.RequestError` becomes a concise `Network error` message and exit code 1.

## Notes

This behavior keeps command implementations small while preserving consistent UX.
