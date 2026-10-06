# Replace Playwright login with cookie extraction

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-replace-playwright-with-cookie-extraction.md`, `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`, `src/superset_cli/auth.py`, `tests/test_auth.py`

## Context

A separate Playwright browser installation and isolated profile complicate login, especially for SSO instances such as `superset.example.com`. Cookie extraction reuses an existing installed-browser session without launching a browser or downloading another one.

## Implemented scope

- `auth login <instance> [--browser ...]` imports target-host cookies into `storage-state.json`.
- Supported choices are `auto`, `chrome`, `edge`, `brave`, `firefox`, `zen`, and `safari`.
- Auto mode tries supported loaders and validates candidates against Superset; explicit browser selection is fail-fast.
- Zen uses the Firefox-format loader with its discovered `cookies.sqlite` path.
- Browser-cookie extraction replaces Playwright in the default runtime login flow.
- Saved state remains compatible with the cookie-auth client and is sensitive.

## Limitations

Only cookies exposed by the loader can be imported. A valid browser session may exist without accessible persisted cookies; an empty loader result does not establish whether the cookie is memory-only. Chromium-family loaders may require a macOS Keychain permission prompt. See the Firefox/Zen recovery ticket for actionable guidance.

## Follow-up

Committed conflict markers and non-example hostnames in the original ticket have been removed. Browser-specific session persistence is not assumed from the browser family alone.
