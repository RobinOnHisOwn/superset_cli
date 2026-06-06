# Cookie header construction helper

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/client.py`, `tests/test_client.py`

## Context

HTTP cookie-header construction is already implemented through `build_cookie_header`. The helper converts parsed storage-state cookies into the header format used by the Superset API client.

## Definition of done

- [x] Cookie name/value pairs are formatted as `name=value`.
- [x] Multiple cookie pairs are joined with `; ` separators.
- [x] Tests verify the final header string for a multi-cookie session.

## Notes

The resulting header is applied when `SupersetClient` is created.
