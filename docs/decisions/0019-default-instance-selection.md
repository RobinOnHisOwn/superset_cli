# 0019: Default instance selection without replacing positional commands

- Status: accepted
- Date: 2026-10-06
- Related: [continuation plan](../plans/2026-10-06-autonomous-todos-continuation.md), [original design](../plans/2026-06-06-default-instance-selection.md), `src/superset_cli/instance_selection.py`, `tests/test_default_instance.py`

## Context

Repeated instance names add friction, but existing valid explicit invocations and write guards must continue to work. Making the first argument optional directly lets an ID consume the instance slot.

## Decision

Resolve positional instance, global `--instance`, `SUPERSET_CLI_INSTANCE`, persisted `default_instance`, then sole configured instance. Unknown selected names do not fall through; empty explicit overrides never fall through to another choice. Multiple/zero instances without a selected name fail with configured names and guidance. `instances use`, `--show`, and `--clear` manage selection. Removal clears a matching persisted default.

Use Typer's supported command subclass hook. The shared adapter accounts for registered options and argument arity and injects a resolved instance before native parsing. Fixed-arity positional instances win. Variadic exports use numeric positionals as IDs when global `--instance` is supplied; an ambiguous numeric instance/export ID otherwise fails with guidance, never guesses. Existing instance-list JSON stays unchanged without a default and gains only `default_instance` when configured.

## Consequences

A narrow parser adapter centralizes compatibility instead of changing every handler signature. Future unusual positional grammars need adapter tests. The explicit numeric-name/export ambiguity is a known safety limit, not a heuristic network operation. Literal `--allow-write` guards are unchanged for omitted-instance invocations.

## Alternatives considered

### Remove positional instances and require a flag everywhere

Would break existing invocations.

### Make the first positional optional without an adapter

Would misassign command targets, particularly numeric IDs and multi-argument datasource commands.
