# Implement default instance selection

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-default-instance-selection.md`, `src/superset_cli/cli.py`, `src/superset_cli/config.py`, `src/superset_cli/models.py`, `README.md`, `docs/architecture/README.md`

## Context

The design ticket `2026-06-06-default-instance-selection.md` proposed a layered precedence for resolving the active instance: positional arg → `--instance` flag → env var → config default → single-configured fallback. This ticket implements that design once it is approved.

## Definition of done

- [x] `default_instance` field added to the config model.
- [x] `instances use <name>` and `instances use --clear` commands exist and persist the default.
- [x] `_require_instance` resolves the active instance via the documented precedence.
- [x] Positional `<instance_name>` on existing subcommands becomes optional.
- [x] Tests cover each level of the precedence and each documented failure case.
- [x] `README.md` and `docs/architecture/README.md` are updated.
- [x] A decision record captures the precedence rules so they do not drift.

## Completion evidence

Implemented with the shared native option/arity adapter before `_require_instance` validation, preserving valid explicit invocations. All precedence levels, multiple-instance refusal, invalid selections, removal, multi-argument commands, compact options, variadic ambiguity, and omitted-instance write refusal are covered. See [continuation evidence](../../plans/2026-10-06-autonomous-todos-continuation.md) and ADR 0019.

## Notes

Ask-first boundary applies because this changes CLI defaults.
