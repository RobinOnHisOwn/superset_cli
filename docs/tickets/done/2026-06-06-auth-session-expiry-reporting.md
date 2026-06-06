# Improve auth session expiry reporting

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/auth.py`, `src/superset_cli/client.py`, `src/superset_cli/cli.py`, `tests/test_auth_status.py`, `tests/test_auth_validate.py`, `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`, `README.md`, `docs/architecture/README.md`

## Context

Saved-session inspection currently reports only whether auth state exists and how many cookies were stored. The browser-login ADR explicitly notes that expired sessions are a normal case and should be handled better over time. The CLI should surface more useful expiry and freshness information from saved auth state.

## Definition of done

- [x] `auth status` exposes richer session metadata, such as cookie expiry or a derived freshness signal, in human and JSON modes.
- [x] The chosen output stays safe for local use and does not leak secret values.
- [x] Tests cover present, expired, and missing-session cases.
- [x] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Prefer metadata derived from the saved storage state rather than making extra live network calls.
