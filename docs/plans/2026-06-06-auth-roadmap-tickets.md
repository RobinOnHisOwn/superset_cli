# Auth roadmap ticket creation plan

**Date:** 2026-06-06

## Goal

Add Markdown tickets for the recommended Superset auth roadmap: preserve session-cookie auth as the default, investigate version-gated API-key auth instead of assuming stable OSS support, evaluate direct JWT login support, and keep guest-token support separate for embedding workflows.

## Planned changes

1. Re-check the existing ticket set for obvious auth-ticket duplicates.
2. Create new `docs/tickets/todo/` tickets for the missing auth roadmap items that are not already tracked.
3. Re-read the new tickets and verify their `Status:` fields and filenames.

## Verification

- Run `find docs/tickets/todo -maxdepth 1 -type f | sort` to confirm the new ticket files exist.
- Run `rg -n "^- Status: todo$" docs/tickets/todo` to confirm each new ticket is marked todo.
- Re-read the created ticket files.

## Decision follow-up

No durable decision change.
