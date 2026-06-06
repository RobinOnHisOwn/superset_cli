# Architecture Doc Maintenance Rule

**Date:** 2026-06-05

## Goal

Require future agents to keep the architecture reference current whenever command-to-code mappings, module responsibilities, or major structural entry points change.

## Planned changes

1. Update `AGENTS.md` to require `docs/architecture/README.md` updates for relevant structural changes.
2. Update `docs/architecture/README.md` with a short maintenance note.
3. Update ADR `0005` because this refines the architecture-reference convention.
4. Verify by re-reading changed files.

## Verification

- Re-read all changed files.
- No code or behavior changes are expected, so test execution is not required for this docs-only change.

## Decision follow-up

Decision record update required: `docs/decisions/0005-architecture-reference-document.md`
