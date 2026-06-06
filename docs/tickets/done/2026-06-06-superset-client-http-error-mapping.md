# Superset client HTTP error mapping

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/client.py`, `tests/test_client.py`

## Context

Superset HTTP error interpretation is already implemented in `SupersetClient._get`. The client converts selected API failures into repository-specific exceptions for the CLI layer.

## Definition of done

- [x] HTTP 401 becomes `AuthExpiredError` with a re-authentication message.
- [x] HTTP 404 becomes `NotFoundError` with the requested resource path.
- [x] Unexpected non-JSON responses also become `AuthExpiredError` because they often indicate an expired session redirect.

## Notes

Other HTTP failures are left to `httpx` to raise normally.
