# Auth ticket correction plan

**Date:** 2026-06-06

## Goal

Correct the auth roadmap tickets so they no longer assume API-key auth is available in current stable Superset OSS, while preserving the broader research trail for version-gated future auth options.

## Planned changes

1. Re-check the auth ticket contents and the consulted Superset documentation evidence.
2. Update the API-key auth tickets to make them version-gated and research-first instead of assumed near-term implementation work.
3. Adjust the JWT auth design ticket wording so it no longer treats API-key auth as an already-established companion mode.
4. Re-read the updated tickets and verify the corrected wording is present.

## Verification

- Re-read the updated auth tickets.
- Run `rg -n "API-key|api-key|stable|Next|unreleased|version-gated|JWT auth" docs/tickets/todo/2026-06-06-*auth*.md docs/tickets/todo/2026-06-06-api-key-*.md` to confirm the corrected wording.

## Decision follow-up

No durable decision change.
