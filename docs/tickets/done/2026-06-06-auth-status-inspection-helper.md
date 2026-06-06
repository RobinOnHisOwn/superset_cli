# Auth status inspection helper

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/auth.py`, `src/superset_agent_cli/client.py`, `tests/test_auth_status.py`, `tests/test_client.py`

## Context

Local auth-state inspection is already implemented through `get_auth_status`. The helper reports whether a storage-state file exists and counts cookies when it does.

## Definition of done

- [x] Missing storage-state files report `authenticated: False` and `cookie_count: 0`.
- [x] Existing storage-state files are parsed through `load_storage_state`.
- [x] The returned payload includes the storage-state path and cookie count.

## Notes

This helper powers the `auth status` command.
