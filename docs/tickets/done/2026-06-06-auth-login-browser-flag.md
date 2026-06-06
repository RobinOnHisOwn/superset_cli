# Add --browser flag to auth login and auth relogin

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-auth-login-browser-flag.md`, `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`, `src/superset_cli/auth.py`, `src/superset_cli/cli.py`, `README.md`, `docs/architecture/README.md`

## Context

The current `login_with_browser` hardcodes Playwright-bundled Chromium. This requires every user to run `playwright install chromium` (~250 MB download) before the first login, even when they already have Chrome, Edge, or Firefox installed. The default behavior should reuse a system browser.

## Definition of done

- [x] `--browser` option exists on `auth login` and `auth relogin` accepting: `chrome`, `chrome-beta`, `chrome-dev`, `msedge`, `msedge-beta`, `msedge-dev`, `chromium`, `firefox`, `webkit`.
- [x] Default is `chrome` (system-installed via Playwright `channel="chrome"`; no Playwright download required).
- [x] Tests cover param forwarding and channel vs engine selection.
- [x] `README.md` and `docs/architecture/README.md` are updated.

## Notes

JSON output shape for `auth login` is unchanged in this ticket (additive `browser_used` field can be a follow-up). Auto-detection of the OS default browser is explicitly out of scope per user direction.
