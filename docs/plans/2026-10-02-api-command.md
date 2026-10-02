# Authenticated custom API command

**Date:** 2026-10-02

## Goal

Make custom Superset API calls usable by agents without handling cookies or CSRF tokens.

## Planned changes

1. Add tests first for custom requests, safe paths, write opt-in, and bounded auth recovery.
2. Add `api INSTANCE PATH` with GET default, explicit method, repeated query params, JSON body/file/stdin, and full response output.
3. Validate auth before requests; import and validate browser cookies once when saved state is missing or rejected. Never retry mutations after sending them.
4. Reject external URLs and disable redirects for custom requests to prevent credential leakage.
5. Update README, architecture, and shared skill source in isolated worktrees.

## Verification

- Focused API tests, full pytest suite, CLI help, build, and offline CLI smoke checks.
- Verified: existing cookie importer validates candidate sessions; shared write guard and body loader exist.
- Proposed: only the new command gets automatic authentication; existing defaults remain unchanged.
- Unknown: live browser-cookie availability; do not access real profiles during tests.

## Decision follow-up

Decision record update required: [0011](../decisions/0011-custom-api-authentication.md).
