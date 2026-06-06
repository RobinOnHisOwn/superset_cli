# Design: default instance selection

## Context

Every CLI command currently takes a positional `<instance_name>`. Many sessions only touch a single configured instance, so this is mildly noisy. The change would alter CLI defaults, which `AGENTS.md` lists as an ask-first boundary. This is a design ticket only; implementation is gated on user approval.

## Candidate approaches

### A. Config-backed default instance

Add an optional `default_instance: prod` to the config file (and a `superset-cli instances use prod` command to set it). When a command omits the positional `<instance_name>`, fall back to the configured default.

- Pros: persistent across sessions; explicit user intent; trivially testable; consistent with how kubectl, gh, etc. handle the same problem.
- Cons: adds a config field; positional `instance_name` becomes optional, which changes Typer signatures across every command.

### B. Environment variable override

Read `SUPERSET_CLI_INSTANCE` and use it when the positional argument is omitted.

- Pros: no config-shape change; easy to swap in CI.
- Cons: invisible state; users won't know why a command runs against an unexpected instance; CI-flavor only.

### C. Explicit global flag

Add `--instance` as a top-level option that callers can supply on the parent CLI before the subcommand. Commands keep the positional argument but skip it if `--instance` is given.

- Pros: explicit per-invocation, no defaults.
- Cons: adds verbosity; doesn't actually reduce typing because the user still has to pass it; mostly a stylistic choice.

### D. Combined precedence (recommended)

Implement A, B, and C with this precedence (highest first):

1. Positional `<instance_name>` on the subcommand (current behavior, unchanged when supplied).
2. `--instance` global flag.
3. `SUPERSET_CLI_INSTANCE` environment variable.
4. `default_instance` field in config.
5. If still missing and there is exactly one configured instance, use it. Otherwise error with the list of configured names.

## Backward compatibility

- All existing invocations that pass an explicit instance name continue to work unchanged.
- New behavior is purely additive: commands that previously errored with `Unknown instance` now optionally succeed when a default is resolved.
- JSON output contracts are unchanged.

## Failure behavior

- No resolved instance and no config: error `No instance specified and no default configured. Add one with 'instances add' or set 'default_instance'.`
- Resolved instance not present in config: error `Default instance 'X' is not configured. Update 'default_instance' or add the instance.`
- Multiple configured instances and no default: error listing the available names.

## Risks

- Hidden behavior: users may not remember which instance is currently default. Mitigate by surfacing it in `instances list` and adding `instances use --show`.
- Typer signature ripple: making `instance_name` `Optional[str]` touches every subcommand. The resolution logic should live in `_require_instance` so signatures change in exactly one helper.

## Recommended next step

Create a follow-up implementation ticket if approved. Implementation should be a single PR that:

1. Adds `default_instance` to the config model.
2. Adds `instances use <name>` and `instances use --clear`.
3. Modifies `_require_instance` to resolve via the documented precedence.
4. Updates README and architecture docs.
5. Adds a decision record explaining the precedence rules.

Follow-up ticket: `2026-06-06-default-instance-selection-implementation.md`.

## Decision follow-up

Decision record update required (only if implementation is approved): add a new ADR under `docs/decisions/` describing the default-instance resolution precedence so it does not drift over time.
