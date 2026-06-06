# Config instance upsert and remove helpers

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/config.py`, `tests/test_instances_add.py`, `tests/test_instances_remove.py`

## Context

Instance mutation helpers are already implemented. `upsert_instance` replaces same-name entries and sorts them, while `remove_instance` filters instances by name.

## Definition of done

- [x] `upsert_instance` removes prior entries with the same name before appending the new one.
- [x] `upsert_instance` sorts instances by name in the returned config.
- [x] `remove_instance` returns a new config with the named instance removed.

## Notes

The sorted upsert behavior is visible in code even where tests focus on resulting command behavior.
