# Superset client request param forwarding

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/client.py`, `tests/test_client.py`

## Context

Low-level request parameter forwarding is already implemented in `SupersetClient._get`. The helper passes query params to `httpx` when present and leaves them unset when absent.

## Definition of done

- [x] `_get(..., params=...)` forwards the supplied params to `httpx.Client.get`.
- [x] `_get(...)` without params passes `None` for request params.
- [x] Tests capture forwarded kwargs to verify the request contract.

## Notes

This helper behavior underpins pagination support and other future query parameters.
