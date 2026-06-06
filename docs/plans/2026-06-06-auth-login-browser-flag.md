# Add --browser flag to auth login and auth relogin

## Goal

Let callers pick which browser Playwright drives during the login flow, defaulting to system-installed Chrome so the first-run no-download path works out of the box.

## API mapping

Playwright supports two ways to launch a browser:

- **System-installed via channel** (no Playwright download): `playwright.chromium.launch_persistent_context(channel="chrome" | "chrome-beta" | "chrome-dev" | "msedge" | "msedge-beta" | "msedge-dev", ...)`.
- **Playwright-bundled engine** (requires `playwright install <engine>`): `playwright.{chromium|firefox|webkit}.launch_persistent_context(...)` with no channel.

The `--browser` value selects between these.

## CLI shape

- `auth login <instance> [--browser chrome]`
- `auth relogin <instance> [--browser chrome]`
- Accepted values: `chrome`, `chrome-beta`, `chrome-dev`, `msedge`, `msedge-beta`, `msedge-dev`, `chromium`, `firefox`, `webkit`.
- Default: `chrome`.
- Invalid value: Typer raises a clear `Invalid value for '--browser'` error before any browser is launched.

## `login_with_browser` signature change

Adds a keyword-only `browser: str = "chrome"` parameter. The function maps the string to the right `(engine, kwargs)` tuple and passes them to `launch_persistent_context`.

Channels and engines:

```
chrome / chrome-beta / chrome-dev / msedge / msedge-beta / msedge-dev
    -> p.chromium.launch_persistent_context(channel=browser, ...)
chromium / firefox / webkit
    -> p.<engine>.launch_persistent_context(...)
```

Any unsupported value raises `ValueError` (CLI-level validation should normally prevent this from reaching the function).

## Tests

- `tests/test_auth.py`:
  - Existing `test_auth_login_invokes_browser_flow` updated so the fake accepts the new `browser` kwarg and asserts `"chrome"` is forwarded by default.
  - New `test_auth_login_forwards_browser_flag` asserts that `--browser firefox` is propagated.
  - New `test_auth_login_rejects_unknown_browser` asserts that an invalid value exits non-zero with a clear error.
- `tests/test_auth_relogin.py`:
  - Update existing fakes to accept the `browser` kwarg.
  - Add one test confirming the `--browser msedge` value forwards through.
- Unit tests are not added for `login_with_browser` directly because it depends on a real Playwright runtime; CLI-level monkeypatching of `superset_cli.cli.login_with_browser` covers wiring.

## Docs

- `README.md` — show `auth login` with and without `--browser`, list valid values.
- `docs/architecture/README.md` — note `--browser` in the auth commands section.

## Decision follow-up

No durable decision change. The existing browser-login ADR (`docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`) already commits to Playwright-driven browser login. This ticket only adds a knob for which Playwright engine/channel is used and changes the default from Playwright-bundled Chromium to system Chrome — a defaults change but within the same ADR.
