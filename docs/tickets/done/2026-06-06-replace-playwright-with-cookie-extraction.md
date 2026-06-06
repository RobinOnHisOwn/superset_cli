# Replace Playwright login with cookie extraction

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-replace-playwright-with-cookie-extraction.md`, `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`, `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`, `src/superset_cli/auth.py`, `src/superset_cli/cli.py`, `pyproject.toml`, `README.md`, `docs/architecture/README.md`

## Context

Playwright-driven login is hostile to users: ~250 MB Chromium download per dev environment, an isolated empty profile that forces sign-in every run, and brittle behavior on OAuth/SSO instances like `superset.example.com`. The user explicitly rejected this approach: "one way that is userfriendly and works for everybody."

Cookie extraction from the user's already-installed browser reuses the session they already have, with zero browser launch and zero extra downloads.

## Definition of done

- [ ] `auth login <instance> [--browser ...]` reads cookies from the chosen (or auto-detected) installed browser and writes them to the existing `storage-state.json` format.
- [ ] `--browser` choices: `auto` (default), `chrome`, `edge`, `brave`, `firefox`, `zen`, `safari`. Auto tries them in priority order and picks the first browser with cookies for the target host.
- [ ] Clear error if no cookies are found: `"No Superset session found for <host> in <browser>. Sign in to <base_url> there first, then re-run."`
- [ ] `auth relogin` command removed (now equivalent to `auth login`).
- [ ] `browser-cookie3` is added as a runtime dependency; `playwright` is removed.
- [ ] Existing read commands continue to work against the new `storage-state.json` without changes.
- [ ] `tests/test_auth.py` covers cookie extraction, auto-detect, missing-cookie failure, and per-browser routing.
- [ ] `tests/test_auth_relogin.py` is deleted.
- [ ] Decision record `0003` is marked superseded; new decision record `0008` documents the cookie-extraction approach and Zen-via-Firefox-format quirk.
- [ ] `README.md` and `docs/architecture/README.md` reflect the new flow.

## Notes

- Zen Browser support: `browser-cookie3` has no native Zen support, but Zen uses Firefox-format `cookies.sqlite`. We construct the Zen profile path and pass it to the library's Firefox loader.
- Session-only cookies that the browser hasn't persisted to disk won't be captured (Chrome doesn't persist; Firefox/Zen do via sessionstore). This is documented behavior.
- macOS Chromium-family triggers a one-time Keychain prompt for the encryption key.
