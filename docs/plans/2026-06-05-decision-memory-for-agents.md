# Decision Memory for Agents

**Date:** 2026-06-05

## Goal

Introduce durable decision documentation so future coding agents can recover not just what this repository does, but why key choices were made.

## Planned changes

1. Create `docs/decisions/README.md` as the decision log index and usage guide.
2. Create initial ADR-style decision records for current durable repo choices:
   - read-only bootstrap scope
   - local config/auth-state storage
   - browser login plus saved storage state for API access
3. Update `AGENTS.md` so agents must consult relevant decision records before planning or editing and must promote lasting choices from plans into `docs/decisions/`.
4. Update `README.md` with a short section pointing humans and agents to the decision log.

## Verification

- Re-read all changed files.
- Confirm the new decision files exist.
- No code or behavior changes are expected, so test execution is not required for this docs-only change.

## Decision follow-up

No durable decision change.
