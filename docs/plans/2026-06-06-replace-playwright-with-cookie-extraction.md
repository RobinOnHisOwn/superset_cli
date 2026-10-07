# Replace Playwright login with cookie extraction

## Goal

Make `auth login` read cookies from the user's installed browser and write them to `storage-state.json`. Remove Playwright entirely. One command, one flow, works against OAuth/SSO instances without forcing a fresh login.

## Approach

`browser-cookie3` (LGPL, +deps `lz4` and `pycryptodomex`) is the cross-platform library that handles Chromium-family AES decryption (macOS Keychain / Linux libsecret / Windows DPAPI) plus Firefox-family plaintext SQLite. Out of the box it supports Chrome, Chromium, Arc, Opera, OperaGX, Brave, Edge, Vivaldi, Firefox, LibreWolf, and Safari (macOS).

Zen Browser is **not** natively supported but stores cookies in Firefox format. We construct the Zen profile path explicitly and reuse the library's Firefox loader.

## Cookie matching

<<<<<<< HEAD
Use the raw hostname from `instance.base_url` (e.g. `superset-raw.studitemps.de`). After loading the cookie jar, filter to cookies whose `domain` matches the target host per the standard browser cookie-sending rule:
=======
Use the raw hostname from `instance.base_url` (e.g. `superset-raw.example.com`). After loading the cookie jar, filter to cookies whose `domain` matches the target host per the standard browser cookie-sending rule:
>>>>>>> docs/agent-efficiency-tickets

```
matches(cookie_domain, host) :=
  host == cookie_domain.lstrip(".") OR
  host.endswith("." + cookie_domain.lstrip("."))
```

<<<<<<< HEAD
This captures both host-only cookies on `superset-raw.studitemps.de` and parent-domain cookies on `.studitemps.de` (which is where Studitemps' SSO actually sets the session). It avoids pulling in unrelated cookies from sibling subdomains.
=======
This captures both host-only cookies on `superset-raw.example.com` and parent-domain cookies on `.example.com` (which is where Example Corp's SSO actually sets the session). It avoids pulling in unrelated cookies from sibling subdomains.
>>>>>>> docs/agent-efficiency-tickets

## CLI shape

- `auth login <instance> [--browser auto|chrome|edge|brave|firefox|zen|safari] [--state-dir ...] [--json]`
- Default `--browser auto`: tries `chrome → edge → brave → firefox → zen → safari` in order, picks the first browser that yields at least one matching cookie.
- On failure: exit 1 with `No Superset session found for <host>. Sign in to <base_url> in your browser first, then re-run.`

## Output

The CLI still writes `storage-state.json` in the same shape, so every existing read command keeps working unchanged:

```json
{
  "cookies": [
    {"name": "...", "value": "...", "domain": "...", "path": "/", "expires": 1234567890.0},
    ...
  ],
  "origins": []
}
```

`expires` is a Unix timestamp (`0` or `None` for session-only cookies). The existing `auth status` expiry logic already handles `None` and non-positive values correctly.

## Code changes

- `pyproject.toml`: remove `playwright`, add `browser-cookie3`.
- `src/superset_cli/auth.py`:
  - Remove `login_with_browser`, `CHANNEL_BROWSERS`, `ENGINE_BROWSERS`, `SUPPORTED_BROWSERS`, `DEFAULT_BROWSER`.
  - Add `SUPPORTED_BROWSERS = ("auto", "chrome", "edge", "brave", "firefox", "zen", "safari")`.
  - Add `import_browser_cookies(*, base_url, storage_state_path, browser) -> dict` that:
    1. Resolves the cookie loader for the named browser (or iterates auto order).
    2. Calls the loader.
    3. Filters cookies by host match.
    4. Serialises matching cookies to `storage-state.json` shape and writes the file.
    5. Returns a small summary dict (`{"browser_used": "chrome", "cookie_count": N}`).
  - Define a `_NoCookiesFound` exception (or use a sentinel return) and surface it cleanly through the CLI.
- `src/superset_cli/cli.py`:
  - Rewrite `auth_login` to call `import_browser_cookies` and print/JSON the result.
  - Remove `auth_relogin` command entirely.
- `tests/test_auth.py`: rewrite around the new behavior with monkeypatched cookie loaders.
- `tests/test_auth_relogin.py`: delete.
- `tests/conftest.py`: existing `instance_setup_with_session` fixture stays valid (the JSON shape is unchanged).

## Tests (TDD)

New tests in `tests/test_auth.py`:

1. `test_auth_login_unknown_instance` — unchanged guard.
2. `test_auth_login_unknown_browser_value` — `--browser netscape` is rejected before any cookie loader runs.
3. `test_auth_login_chrome_writes_storage_state` — monkeypatch `browser_cookie3.chrome` to yield a fake cookiejar for `superset-raw.example.com`; assert `storage-state.json` is written with the expected `cookies` array and JSON shape.
4. `test_auth_login_filters_to_target_host` — fake jar includes cookies for unrelated hosts; assert only the matching ones land in the file.
5. `test_auth_login_includes_parent_domain_cookies` — fake jar has a `.example.com` cookie; assert it's captured for host `superset-raw.example.com`.
6. `test_auth_login_no_cookies_found_errors` — fake jar has no matching cookies; assert exit code 1 and the documented message.
7. `test_auth_login_auto_picks_first_browser_with_cookies` — auto-detect order; first two loaders raise/return empty, third returns cookies; assert the third one is the one used.
8. `test_auth_login_json_output` — `--json` returns `{"instance": ..., "base_url": ..., "browser_used": ..., "cookie_count": ..., "storage_state_path": ...}`.
9. `test_auth_login_zen_uses_firefox_format` — monkeypatch the Zen path resolver to return a fixture cookies.sqlite, assert it's loaded via the Firefox loader.

## Decision follow-up

Decision record update required:
- Mark `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md` as `Superseded by 0008`.
- Add `docs/decisions/0008-cookie-extraction-from-installed-browsers.md` documenting:
  - The shift to cookie extraction.
  - The `browser-cookie3` dependency and rationale.
  - The Zen-via-Firefox-format approach.
  - Honest caveats (session-cookie persistence, Keychain prompt, OAuth flow assumption that user is already signed in).
