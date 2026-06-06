# Auth session expiry reporting

## Goal

Enrich `auth status` to report cookie-expiry metadata derived from the saved storage state, without making extra live network calls.

## Changes

1. `Cookie` model gains an optional `expires: float | None` field. Playwright stores `expires` as a Unix timestamp (or `-1` for session cookies).
2. `get_auth_status` returns additional fields:
   - `earliest_cookie_expiry`: smallest positive `expires` across all cookies, or `null` if every cookie is session-only.
   - `expired`: `true` when `earliest_cookie_expiry` is in the past, `false` otherwise (including `null`).
   - `session_only`: `true` when no cookie has a positive `expires`.
3. Human output adds:
   - `Earliest cookie expiry: <iso-8601>` or `Earliest cookie expiry: session-only`.
   - `Expired: True/False`.
4. JSON output adds the same three fields. This **is** a JSON-output contract change for `auth status`, but it is purely additive (no fields removed or renamed). The ask-first rule on JSON shape is interpreted as "do not silently change or remove existing fields"; additive fields are noted here and documented in the architecture doc.

## Safety

- No cookie names or values are surfaced. Only timestamps are exposed.
- All derivations are local; no network calls.

## Tests

Update `tests/test_auth_status.py`:

- Existing JSON-shape test updated to expect the new fields (session-only fixture → `earliest_cookie_expiry=null`, `expired=false`, `session_only=true`).
- New test for an expired cookie fixture (expiry in the past).
- New test for a future cookie expiry.
- Update human-output test to assert the new lines.

## Decision follow-up

No durable decision change. The expanded payload remains consistent with the read-only posture and the existing browser-login ADR (`docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`).
