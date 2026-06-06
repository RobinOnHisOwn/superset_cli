# Retrospective feature tickets

**Date:** 2026-06-06

## Goal

Create retrospective `done` tickets in `docs/tickets/done/` for already-implemented user-facing commands and internal helper behaviors that are visible in the current codebase, tests, and docs.

## Planned changes

1. Read the current source files and tests that define implemented commands and helper behaviors.
2. Derive a ticket list that covers:
   - all current user-facing commands
   - major internal helper behaviors visible in code, tests, or docs
3. Create retrospective Markdown tickets in `docs/tickets/done/` using the standard ticket format.
4. Re-read the created tickets and verify the full ticket list exists in `docs/tickets/done/`.

## Verification

- Re-read the created retrospective tickets in `docs/tickets/done/`.
- Run `find docs/tickets/done -maxdepth 1 -type f | sort` to confirm the files were created.
- Run `rg -n "^- Status: done$" docs/tickets/done` to confirm each retrospective ticket is marked done.

## Decision follow-up

No durable decision change.
