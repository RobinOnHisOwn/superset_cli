# Browser login persistent context flow

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/auth.py`, `tests/test_auth.py`

## Context

Interactive browser login is already implemented in `login_with_browser`. It launches a persistent Chromium context, opens the target base URL, waits for human confirmation, and saves storage state.

## Definition of done

- [x] The helper creates parent directories for the browser profile and storage-state file.
- [x] Chromium launches with a persistent user data directory and navigates to the Superset base URL.
- [x] After manual confirmation, storage state is saved and the browser context is closed.

## Notes

Tests validate the command handoff into this helper rather than the live Playwright session itself.
