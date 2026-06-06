# Architecture Overview Doc

**Date:** 2026-06-05

## Goal

Add a concise but agent-usable architecture overview so future agents can recover both the high-level structure of the repository and the exact code/test entry points for each current command.

## Planned changes

1. Create `docs/architecture/README.md` with a high-level architecture overview and an agent-focused reference section.
2. Update `README.md` to point readers to the architecture doc.
3. Update `AGENTS.md` to mention `docs/architecture/README.md` as a structural reference.
4. Verify by re-reading changed files and confirming the new architecture doc exists.

## Verification

- Re-read all changed files.
- Confirm `docs/architecture/README.md` exists.
- No code or behavior changes are expected, so test execution is not required for this docs-only change.

## Decision follow-up

Decision record update required: `docs/decisions/0004-decision-memory-system.md`
