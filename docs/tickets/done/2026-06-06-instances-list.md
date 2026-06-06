# Instances list command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/config.py`, `tests/test_cli.py`, `tests/test_instances_add.py`, `docs/architecture/README.md`

## Context

`instances list` is already implemented. It loads configured instances from local config and renders either human-readable output or compact JSON.

## Definition of done

- [x] `instances list` reads configured instances from the CLI config.
- [x] Human output shows `name: base_url` lines or `No instances configured.` when empty.
- [x] `instances list --json` returns the `{"instances":[...]}` shape.

## Notes

The current contract is visible in `tests/test_cli.py` and `tests/test_instances_add.py`.
