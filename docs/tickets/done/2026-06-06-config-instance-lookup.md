# Config instance lookup helper

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/config.py`, `src/superset_cli/cli.py`, `tests/test_instances_remove.py`, `tests/test_auth.py`, `tests/test_dashboards.py`

## Context

Instance lookup is already implemented through `get_instance`. The CLI uses it to resolve configured instances and reject unknown names before doing work.

## Definition of done

- [x] `get_instance` returns the first matching instance by name.
- [x] `get_instance` returns `None` when no instance matches.
- [x] CLI commands reuse lookup results for consistent known-instance guards.

## Notes

The helper is intentionally small and shared.
