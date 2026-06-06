# More Superset API gap ticket creation plan

**Date:** 2026-06-06

## Goal

Add Markdown tickets for additional read-only Superset API feature gaps that were identified during API research and are not already tracked in `docs/tickets/`.

## Planned changes

1. Re-check the current ticket set for obvious duplicates.
2. Create new `docs/tickets/todo/` tickets for the additional API gaps.
3. Re-read the new tickets and verify their `Status:` fields and filenames.

## Verification

- Run `find docs/tickets/todo -maxdepth 1 -type f | sort` to confirm the new ticket files exist.
- Run `rg -n "^- Status: todo$" docs/tickets/todo` to confirm each new ticket is marked todo.
- Re-read the created ticket files.

## Decision follow-up

No durable decision change.
