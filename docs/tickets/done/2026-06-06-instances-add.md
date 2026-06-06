# Instances add command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/config.py`, `src/superset_cli/models.py`, `tests/test_instances_add.py`, `tests/test_config.py`, `docs/architecture/README.md`

## Context

`instances add <name> <base_url>` is already implemented. It validates instance data through the config models, upserts the instance, and saves the config.

## Definition of done

- [x] `instances add` persists the instance to config storage.
- [x] A success message confirms the saved instance name.
- [x] Added instances become visible in later `instances list --json` output.

## Notes

Base URL validation and normalization are implemented in `models.py`.
