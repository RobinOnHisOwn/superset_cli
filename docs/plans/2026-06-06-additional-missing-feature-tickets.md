# Additional missing feature ticket creation plan

**Date:** 2026-06-06

## Goal

Add Markdown tickets for missing Superset read and write feature areas that were identified during API research and are not already represented in `docs/tickets/`.

## Planned changes

1. Re-check the existing ticket set for obvious duplicates.
2. Create new `docs/tickets/todo/` tickets for missing read features that are not already tracked.
3. Create new `docs/tickets/todo/` tickets for missing write feature areas, using research or scope-gated code tickets where the current read-only ADR blocks immediate implementation.
4. Re-read the new tickets and verify their `Status:` fields and filenames.

## Verification

- Run `find docs/tickets/todo -maxdepth 1 -type f | sort` to confirm the new files exist.
- Run `rg -n "^- Status: todo$" docs/tickets/todo` to confirm each new ticket is marked todo.
- Re-read the newly created tickets.

## Decision follow-up

No durable decision change.
