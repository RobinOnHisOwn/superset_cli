# Implement default instance selection

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-default-instance-selection.md`, `src/superset_cli/cli.py`, `src/superset_cli/config.py`, `src/superset_cli/models.py`, `README.md`, `docs/architecture/README.md`

## Context

The design ticket `2026-06-06-default-instance-selection.md` proposed a layered precedence for resolving the active instance: positional arg → `--instance` flag → env var → config default → single-configured fallback. This ticket implements that design once it is approved.

## Definition of done

- [ ] `default_instance` field added to the config model.
- [ ] `instances use <name>` and `instances use --clear` commands exist and persist the default.
- [ ] `_require_instance` resolves the active instance via the documented precedence.
- [ ] Positional `<instance_name>` on existing subcommands becomes optional.
- [ ] Tests cover each level of the precedence and each documented failure case.
- [ ] `README.md` and `docs/architecture/README.md` are updated.
- [ ] A decision record captures the precedence rules so they do not drift.

## Notes

Ask-first boundary applies because this changes CLI defaults.
