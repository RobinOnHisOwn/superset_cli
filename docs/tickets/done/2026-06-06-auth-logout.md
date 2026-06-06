# Auth logout command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/auth.py`, `tests/test_auth_logout.py`, `docs/architecture/README.md`

## Context

`auth logout <instance>` is already implemented. It removes saved auth-state data for a known instance and preserves other instances.

## Definition of done

- [x] Unknown instances and missing auth state exit with clear errors.
- [x] Existing instance auth-state directories are removed recursively.
- [x] Human and JSON output confirm the removed auth-state instance name.

## Notes

Tests cover isolation so one instance logout does not affect another.
