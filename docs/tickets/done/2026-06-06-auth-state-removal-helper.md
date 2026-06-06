# Auth state removal helper

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/auth.py`, `tests/test_auth_logout.py`

## Context

Recursive auth-state removal is already implemented through `remove_auth_state`. The helper removes the entire per-instance auth directory and returns the removed path.

## Definition of done

- [x] `remove_auth_state` targets the per-instance state directory.
- [x] Removal uses recursive deletion with `ignore_errors=True`.
- [x] Command-level tests verify that the target instance directory disappears while other instance state remains intact.

## Notes

The command layer handles the precondition checks before calling this helper.
