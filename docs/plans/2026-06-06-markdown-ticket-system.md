# Markdown ticket system

**Date:** 2026-06-06

## Goal

Add a lightweight Markdown ticket system for repo work and teach agents how to use it safely through `AGENTS.md`.

## Planned changes

1. Add a new `docs/tickets/` documentation area with:
   - `docs/tickets/README.md`
   - `docs/tickets/template.md`
   - `docs/tickets/todo/.gitkeep`
   - `docs/tickets/in-progress/.gitkeep`
   - `docs/tickets/done/.gitkeep`
2. Document the ticket workflow in `docs/tickets/README.md`, including:
   - purpose and scope
   - lifecycle across `todo`, `in-progress`, and `done`
   - filename convention
   - duplicate-handling guidance
   - boundaries between tickets, plans, and decision records
3. Add a canonical ticket template in `docs/tickets/template.md` with required metadata and actionable sections.
4. Update `AGENTS.md` with a dedicated Markdown ticket system section that allows proactive ticket creation, requires an obvious-duplicate check, and preserves the existing plan/decision workflow.
5. Update `docs/index.md` to include the new top-level documentation area and route readers to it.
6. Update `docs/glossary.md` with repository terms introduced by the new workflow.
7. Add a new decision record in `docs/decisions/` to capture the durable choice to use a Markdown ticket system in-repo.
8. Verify the change by re-reading the touched docs and listing the new ticket files.

## Verification

- Read the updated `AGENTS.md`, `docs/index.md`, `docs/glossary.md`, `docs/tickets/README.md`, and `docs/decisions/0006-markdown-ticket-system.md`.
- Run `find docs/tickets -maxdepth 2 -type f | sort` to confirm the new ticket area exists as expected.

## Decision follow-up

Decision record update required: `docs/decisions/0006-markdown-ticket-system.md`
