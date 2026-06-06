# Superset client lifecycle helpers

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/client.py`, `tests/test_client.py`, `tests/test_auth_validate.py`, `tests/test_dashboards.py`, `tests/test_charts.py`, `tests/test_datasets.py`, `tests/test_databases.py`

## Context

Client resource management is already implemented in `SupersetClient`. The class opens an `httpx.Client`, supports `close()`, and works as a context manager so command handlers reliably release network resources.

## Definition of done

- [x] `close()` closes the underlying `httpx.Client`.
- [x] `__enter__` and `__exit__` support `with SupersetClient(...) as client:` usage.
- [x] Command tests verify that clients are closed after command execution.

## Notes

Lifecycle management is part of the normal command execution path.
