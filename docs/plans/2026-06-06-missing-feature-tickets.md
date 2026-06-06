# Missing feature ticket creation plan

**Date:** 2026-06-06

## Goal

Add small, actionable Markdown tickets for the most defensible missing read-only and CLI-ergonomic features identified from the current codebase and Superset API surface.

## Planned changes

1. Re-check `docs/tickets/` for obvious duplicate tickets.
2. Create new `docs/tickets/todo/` tickets for the missing feature areas that are not already tracked.
3. Keep tickets small where possible and use a research ticket when a feature area is still too broad for a single implementation ticket.
4. Re-read the created tickets and verify their `Status:` fields and filenames.

## Verification

- Run `find docs/tickets/todo -maxdepth 1 -type f | sort` to confirm the new ticket files exist.
- Run `rg -n "^- Status: todo$" docs/tickets/todo` to confirm each new ticket is marked todo.
- Re-read the created ticket files.

## Decision follow-up

No durable decision change.
