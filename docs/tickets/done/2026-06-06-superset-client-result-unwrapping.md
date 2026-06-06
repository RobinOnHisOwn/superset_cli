# Superset client result unwrapping

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/client.py`, `tests/test_client.py`, `docs/architecture/README.md`

## Context

Single-resource response normalization is already implemented in the Superset client. Methods for current-user and resource getters unwrap Superset `{"result": ...}` payloads before returning them to callers.

## Definition of done

- [x] `get_dashboard`, `get_chart`, `get_dataset`, and `get_database` return the inner resource object.
- [x] `get_current_user` returns the inner user object.
- [x] List methods intentionally keep the full list envelope so callers can access both `count` and `result`.

## Notes

This behavior keeps CLI formatting code simple and consistent.
