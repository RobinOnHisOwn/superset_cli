# Validate imported browser sessions during auth login

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-08-27
- Related: `docs/plans/2026-08-27-auth-login-live-validation.md`, `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`, `src/superset_cli/cli.py`, `tests/test_auth.py`

## Context

`auth login` currently reports success after finding and saving any matching browser cookie. A stale Zen cookie reproduced a false-success result: import succeeded, while the first Superset request returned HTTP 401.

## Definition of done

- [x] Login validates the imported state against the live current-user endpoint.
- [x] Rejected sessions exit non-zero and remove the newly written auth state.
- [x] Network failures exit non-zero without deleting state of unknown validity.
- [x] Success JSON remains backward compatible.
- [x] Focused and full verification pass.

## Notes

Candidate fallback and in-memory browser-cookie extraction are deliberately deferred.
