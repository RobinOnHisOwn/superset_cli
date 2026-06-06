# Repository Glossary

**Date:** 2026-06-05

## Goal

Add a glossary of repository-specific terms so future agents and humans can interpret local documentation, workflow language, and architecture descriptions consistently.

## Planned changes

1. Create `docs/glossary.md` with concise definitions for recurring repository terms.
2. Update `docs/index.md`, `AGENTS.md`, and `README.md` to point to the glossary where useful.
3. Update ADR `0004` because this adds a new top-level documentation area to the layered documentation system.
4. Verify by re-reading changed files and confirming the glossary exists.

## Verification

- Re-read all changed files.
- Confirm `docs/glossary.md` exists.
- No code or behavior changes are expected, so test execution is not required for this docs-only change.

## Decision follow-up

Decision record update required: `docs/decisions/0004-decision-memory-system.md`
