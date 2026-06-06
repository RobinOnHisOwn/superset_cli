# Config load and save helpers

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/config.py`, `tests/test_config.py`, `tests/test_instances_add.py`

## Context

Local config persistence is already implemented in `config.py`. The helper layer loads missing config as empty, reads YAML into models, and saves config back to the default or requested path.

## Definition of done

- [x] `load_config` returns an empty `Config` when the file is missing.
- [x] `load_config` reads YAML instances into `Config` models.
- [x] `save_config` creates parent directories and writes YAML from the model state.

## Notes

These helpers are the persistence foundation for instance commands.
