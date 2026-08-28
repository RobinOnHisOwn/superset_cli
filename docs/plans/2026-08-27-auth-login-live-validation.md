# Auth login live validation

**Date:** 2026-08-27

> **Required workflow:** Implement test-first and verify the focused tests before the full suite.

## Goal

Prevent `auth login` from reporting success when a browser cookie exists on disk but Superset rejects it.

## Planned changes

1. Add CLI tests proving a valid imported session is checked through `SupersetClient.get_current_user()` and the client is closed.
2. Add a failing-session test proving rejected cookies produce a precise non-zero error and remove the newly written per-instance auth state.
3. Add a network-failure test proving validation exits non-zero but preserves the imported state because validity is unknown.
4. Implement the smallest validation step directly in `auth_login` without changing its JSON success shape.
5. Document the live-validation behavior in `README.md`, `docs/architecture/README.md`, and ADR 0008.

## Verification

- `uv run pytest tests/test_auth.py -v`
- `uv run pytest -v`
- `uv run superset-cli --help`
- `uv build`
- `git diff --check`

## Decision follow-up

Decision record update required: `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`.
