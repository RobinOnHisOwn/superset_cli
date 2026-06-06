# 0009: Write commands require `--allow-write` per invocation

- Status: accepted
- Date: 2026-06-06
- Related: [`docs/decisions/0001-read-only-bootstrap-scope.md`](0001-read-only-bootstrap-scope.md), `AGENTS.md` "Write-command contract" section, `src/superset_cli/cli.py` (future shared helper)

## Context

The CLI's bootstrap scope ([ADR 0001](0001-read-only-bootstrap-scope.md)) is strictly read-only. Several `todo/` tickets propose eventual write capabilities (chart, dashboard, dataset, database, saved-query, tag, theme, sqllab, asset-import, security-admin). Before any of those land, the project needs a hard contract that prevents the read-only posture from drifting silently and that protects users from unintended mutation.

`AGENTS.md` already says agents must ask before "expanding from read-only into write-capable Superset operations." That is behavioral guidance for agents. It does not constrain the CLI itself, and it does not protect humans against typos or copy-paste mistakes. A separate, mechanical contract is needed for the CLI's own surface.

## Decision

Every CLI command that mutates Superset state requires an explicit `--allow-write` flag on every invocation. Default off.

Concretely:

- The flag is a literal CLI argument named `--allow-write`. No short form.
- The flag is per-invocation only. It is never persisted in the config file, never read from an environment variable, and never defaulted on.
- Without the flag, the command exits non-zero with a clear message naming the flag and describing the mutation it would have performed.
- The check is centralised in a shared helper in `src/superset_cli/cli.py`, so write commands cannot accidentally forget it.
- Help text for every write command must include: "Required to actually perform the write. Without it the command is a dry-run."
- The check applies to every write command, including operations that look idempotent.
- `--allow-write` is never granted by a confirmation prompt, a config flag, an environment variable, or a parent command — only by the literal CLI argument on the same invocation.

## Consequences

Positive:

- Unintended write calls (typos, agent overshoot, copy-paste from documentation) fail safe.
- Human and agent operators see the same friction. The policy cannot drift through agent-only conventions.
- The read-only product posture remains visible in every future write surface — the flag itself is the documentation.
- Scripted/CI use stays explicit: callers must put `--allow-write` in their wrapper, which becomes grep-able evidence of intent.

Negative / honest caveats:

- Friction for power users who run write commands regularly. They will alias the flag away — that is their informed choice, and the alias is the audit trail. The flag's purpose is to prevent the *unintended* destructive call, not the deliberate one.
- Adds boilerplate to every write command's option list. Mitigated by the shared helper.
- Future write commands must remember to wire through the helper. The helper should make it impossible to skip (e.g. by requiring the option in the helper's signature).

## Alternatives considered

- **Interactive confirmation prompt instead of a flag.** Breaks scripting and CI, can be bypassed by agents in ways that leave no audit trail, and the friction shows up only at runtime instead of being visible in the call site.
- **`--dry-run` opt-in inverted to `--apply`.** Same effect with different naming. `--allow-write` reads as a permission grant (what it is) rather than a mode toggle (what it isn't). Permission framing maps more directly to the safety intent.
- **Config-level `allow_writes: true`.** Defeats the per-invocation guard — one ill-considered edit to a config file would silently re-enable destructive operations across every subsequent call.
- **Environment variable opt-in (`SUPERSET_CLI_ALLOW_WRITES=1`).** Same problem as the config flag, plus the value can be inherited from a parent shell the user has forgotten about.
- **Rely on `AGENTS.md` "ask first" guidance alone.** Insufficient: agents can misread "asked once" as standing authorization, and the rule does not protect humans against unintended invocations.

## Rollout

- This ADR is binding for every new write command added to the CLI. There are currently zero write commands in the implemented surface (per [ADR 0001](0001-read-only-bootstrap-scope.md)), so the contract has zero immediate code impact.
- The first write-command ticket that ships must include the shared `--allow-write` helper in `src/superset_cli/cli.py` and at least one test that proves the command refuses to run without the flag.
- The `2026-06-06-write-scope-expansion-decision.md` ticket should be updated to reference this ADR before any write ticket is moved out of `todo/`.
