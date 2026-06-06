# Reusable Documentation Templates

**Date:** 2026-06-05

## Goal

Add reusable documentation templates so future agents can create plans, decision records, and final reports with less drift from repository conventions.

## Planned changes

1. Create `docs/templates/` with a short index and reusable Markdown templates.
2. Update `docs/index.md`, `AGENTS.md`, `docs/plans/README.md`, and `docs/decisions/README.md` to point to the templates.
3. Update ADR `0004` because this expands the layered documentation system with canonical templates.
4. Verify by re-reading changed files and confirming the template files exist.

## Verification

- Re-read all changed files.
- Confirm the new template files exist.
- No code or behavior changes are expected, so test execution is not required for this docs-only change.

## Decision follow-up

Decision record update required: `docs/decisions/0004-decision-memory-system.md`
