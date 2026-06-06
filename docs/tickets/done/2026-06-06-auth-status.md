# Auth status command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/auth.py`, `src/superset_cli/client.py`, `tests/test_auth_status.py`, `tests/test_client.py`, `docs/architecture/README.md`

## Context

`auth status <instance>` is already implemented. It requires saved storage state, inspects the stored session, and reports whether the local auth state appears present.

## Definition of done

- [x] Unknown instances and missing storage state are rejected.
- [x] `--json` returns `authenticated`, `storage_state_path`, and `cookie_count` alongside instance metadata.
- [x] Human output reports authentication state, storage-state path, and cookie count.

## Notes

Cookie counting depends on `get_auth_status` and `load_storage_state`.
