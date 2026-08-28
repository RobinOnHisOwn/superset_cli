# 0008: Cookie extraction from installed browsers instead of Playwright

- Status: accepted
- Date: 2026-06-06
- Supersedes: [0003 Browser login with Playwright and saved storage state](0003-browser-login-with-playwright-and-saved-storage-state.md)
- Related: `src/superset_cli/auth.py`, `src/superset_cli/cli.py`, `tests/test_auth.py`, `pyproject.toml`, `README.md`, `docs/architecture/README.md`

## Context

ADR 0003 chose Playwright-driven browser login as the way to acquire a Superset session and persist it as `storage-state.json`. In practice that approach has hostile UX:

- Forces every developer to download Playwright's bundled Chromium (~250 MB) before first run.
- Launches a fresh, empty Chromium profile, so users must re-sign-in with Google/SSO every time even if they're already logged in to Superset elsewhere.
- Locks the storage-state acquisition behind a real interactive Chromium window, which is awkward on headless boxes and incompatible with the user's actual default browser of choice (e.g. Zen).

The user explicitly rejected this trade-off: they wanted one auth flow that "works for everybody" without an extra browser install or an isolated session.

## Decision

Drop Playwright entirely from runtime dependencies. Acquire the Superset session by **extracting cookies from the user's already-installed browser** and writing them to the same `storage-state.json` shape the existing client code consumes. Use [`browser-cookie3`](https://github.com/borisbabic/browser_cookie3) (LGPL) to handle the cross-platform encryption details.

Supported browsers in v1:

- Chrome, Edge, Brave (Chromium-family, AES-decrypted via the OS keystore)
- Firefox (plaintext SQLite)
- Safari on macOS (BinaryCookies parser shipped by `browser-cookie3`)
- Zen — Firefox-format under a custom profile path; we resolve the path explicitly and reuse `browser-cookie3`'s Firefox loader

Default browser is `auto`: try `chrome → edge → brave → firefox → zen → safari` in order, validate matching cookies against Superset, and pick the first accepted session. Explicit browser selection remains fail-fast.

The `storage-state.json` schema is unchanged, so every read command keeps working without modification.

Treat cookie extraction as tentative until Superset accepts the imported session. `auth login` validates each saved candidate through the current-user endpoint before reporting success. Auto mode skips rejected browser candidates; explicit rejection or exhaustion removes the imported state and exits non-zero. If validation cannot run because of a network failure, the CLI stops fallback, exits non-zero, and preserves the current state because its validity is unknown.

## Consequences

Positive:

- Single one-step `auth login <instance>` flow: no browser launch, no fresh sign-in, works against OAuth/SSO instances.
- No 250 MB browser download, no Playwright runtime, no Chromium version drift.
- Works with whatever browser the user already runs day-to-day, including Zen.
- Cross-platform out of the box (macOS, Linux, Windows) via `browser-cookie3`.

Negative / honest caveats:

- The user must already be signed in to Superset in the chosen browser. If not, the CLI errors with a clear message asking them to sign in there first. This is a regression in "log me in from scratch" UX but a much bigger improvement in "reuse my existing session" UX, which is the actual common case.
- Chrome-family cookie decryption triggers a one-time macOS Keychain prompt for the `Chrome Safe Storage` entry. After "Always Allow" it's silent.
- Session-only cookies that the browser hasn't persisted to disk are not captured. Chrome doesn't persist session cookies between launches; Firefox/Zen do via `sessionstore`. A stale on-disk cookie can still be extracted while a fresh browser-only session exists; live validation now rejects that false-success case explicitly.
- `browser-cookie3` occasionally breaks when a browser updates its encryption scheme (notably Chrome on Windows v130+ moved to per-process binding). We accept the upstream-fix cadence as the cost of not maintaining our own decryptor.
- LGPL transitive license: dynamic import (the only mode we use) is permitted and does not affect this repository's effective license.

## Alternatives considered

- **CDP-attach to a running Chrome** (`--remote-debugging-port=9222`). Forces the user to launch Chrome with a specific flag and doesn't help Zen/Firefox users at all. Rejected as not universal.
- **Point Playwright at the user's main Chrome profile dir.** Chrome locks its `User Data` directory while running, so this fails whenever the user already has Chrome open. Same problem for Zen. Rejected as fragile.
- **Roll our own cookie extractor.** Cross-platform Chromium decryption (Keychain + libsecret + DPAPI) is ~300-500 LOC we'd have to maintain forever. `browser-cookie3` already does this. Rejected as not worth the maintenance burden.
- **Keep Playwright as a fallback under `[playwright]` extra.** Adds a second auth flow with its own failure modes and doubles the docs/test surface. User explicitly asked for one flow. Rejected.

## Migration notes

- `auth login` keeps the same command name but changes implementation. The CLI surface gains the new `--browser` semantics described above.
- `auth relogin` is removed. Re-running `auth login` is equivalent.
- `storage-state.json` format is unchanged, so any user with a previously-saved session from the Playwright flow keeps working without re-running `auth login`.
