# Per-invocation HTTP timeouts

**Date:** 2026-10-06

## Goal

Expose a finite positive HTTP timeout without changing the 30-second default or retrying mutations.

## Planned changes

1. Bring the open timeout ticket from the older local checkout into this fresh worktree and mark it in progress. Chart-data exits and documentation links are already implemented on origin/main (29 focused tests passed).
2. Add failing tests for the root `--timeout` option, request forwarding, validation before network/browser access, invocation isolation, and mutation timeout diagnostics.
3. Use a context-local timeout, matching the existing invocation-scoped context pattern, in shared clients and direct JWT authentication requests. Keep HTTPX phase/inactivity semantics, bounded auth recovery, and write guards.
4. Update help, README, the timeout decision record, and the completed ticket.

## Verification

- Verified: current HTTP clients use 30 seconds; HTTPX documents connect/read/write/pool timeouts rather than a total deadline: https://www.python-httpx.org/advanced/timeouts/.
- Verified: ADRs 0011 and 0018 require bounded authentication recovery and no sent-mutation retries.
- Proposed: one root option before the command, scoped and reset per invocation.
- Run focused red/green tests, full pytest suite, CLI help/manual invalid-input smoke checks, and `uv build` through direnv.
- No live requests or credential access.

## Results

- Implemented the root option, context-scoped forwarding, explicit JWT forwarding, and bounded timeout diagnostics without changing retries or write guards.
- Initial tests failed on the missing option; focused timeout/API/JWT/client checks passed (100 tests).
- Full suite: 850 passed, 13 skipped. Final docs-link/timeout checks: 15 passed.
- CLI help, custom-value and invalid-value manual smoke checks, wheel/source build, and `git diff --check` passed.
- The first manual smoke put root `--config` after the subcommand and failed; correcting placement produced exit 0.
- `specdocs_validate` reported an existing architecture filename-pattern error in the tool's original workspace. Repository docs-link tests passed in this worktree; no unrelated formatting changes were made.
- No live Superset verification. The API-key todo remains blocked on server capability verification.

## Decision follow-up

Decision record update required: `docs/decisions/0021-per-invocation-http-timeout.md`.
