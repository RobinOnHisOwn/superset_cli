# Instances remove command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/config.py`, `tests/test_instances_remove.py`, `docs/architecture/README.md`

## Context

`instances remove <name>` is already implemented. It removes a known instance from config while leaving auth-state files untouched.

## Definition of done

- [x] Unknown instances exit with an error message.
- [x] Known instances are removed from config persistence.
- [x] Human and JSON output contracts report the removed instance name without deleting auth state.

## Notes

Tests also cover leaving other configured instances intact.
