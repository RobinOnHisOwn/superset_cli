# Auth path derivation helpers

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/auth.py`, `src/superset_agent_cli/cli.py`, `tests/test_auth.py`, `tests/test_auth_logout.py`

## Context

Auth-state path derivation is already implemented through helper functions in `auth.py`. Commands use these helpers to keep per-instance state under a predictable directory layout.

## Definition of done

- [x] `get_instance_dir` maps an instance name to its state directory.
- [x] `get_storage_state_path` derives `storage-state.json` under the instance directory.
- [x] `get_profile_dir` derives the persistent browser profile directory under the instance directory.

## Notes

The path contract is visible in both code and command tests.
