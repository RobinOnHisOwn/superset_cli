# Auth re-login helper

> **Superseded by [Replace Playwright login with cookie extraction](2026-06-06-replace-playwright-with-cookie-extraction.md).** The `auth relogin` command was removed when the underlying auth flow stopped being a browser-launch interaction — `auth login` is now idempotent (re-reads cookies from the user's installed browser), so a separate "re-login" command is no longer meaningful.

## Goal

Add `auth relogin <instance>` that performs a logout (remove saved auth state) followed by a fresh `auth login` browser flow, in one command.

## Behavior

- Resolves the instance via existing `_require_instance` checks.
- If saved auth state exists, removes it; if it does not, proceeds straight to login (no error).
- Launches the browser-login flow that `auth login` already uses.
- On success, prints (or `--json` emits) the same payload shape as `auth login` plus a `relogged_in: true` field.

## Why not just chain `auth logout && auth login`?

- `auth logout` exits non-zero when no state exists, which means scripting `logout && login` fails in the common "expired session, never logged out cleanly" case.
- A single command is what every related ticket assumes ("re-login flow"), and it gives the next ticket (`auth-session-expiry-reporting`) a single place to point users to.

## Tests

- `tests/test_auth_relogin.py`:
  - unknown instance
  - existing state is removed before login
  - missing state proceeds straight to login
  - JSON output shape
  - browser login is invoked

## Decision follow-up

No durable decision change. Keeps the existing browser-login model.
