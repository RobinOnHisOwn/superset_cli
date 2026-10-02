# Auth login automatic candidate fallback

**Date:** 2026-08-27

## Goal

Make `auth login --browser auto` skip browser cookies rejected by Superset and continue to the next installed-browser candidate.

## Planned changes

1. Add failing tests for stale-first/valid-second auto selection, all-stale cleanup, explicit-browser rejection, and network failure preservation.
2. Extend the existing browser-cookie import loop with a validation callback; do not add another auth flow.
3. Keep explicit browser selection fail-fast and preserve the current success JSON shape.
4. Update README, architecture documentation, and ADR 0008.

## Verification

- `uv run pytest tests/test_auth.py -v`
- `uv run pytest -v`
- `uv run superset-cli --help`
- `uv build`
- `git diff --check`

## Decision follow-up

Decision record update required: `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`.
