# Try the next browser when an imported session is stale

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-08-27
- Related: `docs/plans/2026-08-27-auth-login-auto-fallback.md`, `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`, `src/superset_cli/auth.py`, `src/superset_cli/cli.py`, `tests/test_auth.py`

## Context

Auto login currently picks the first browser containing matching cookies. Live validation can reject that cookie, but the CLI does not continue to a later browser that may contain a valid session.

## Definition of done

- [x] Auto mode skips rejected browser sessions and accepts the first live one.
- [x] Explicit browser mode remains fail-fast.
- [x] All rejected candidates remove imported auth state and exit non-zero.
- [x] Network failures preserve the current candidate and stop fallback.
- [x] Success JSON remains backward compatible.

## Notes

Zen in-memory cookie extraction and extra profile discovery remain out of scope.
