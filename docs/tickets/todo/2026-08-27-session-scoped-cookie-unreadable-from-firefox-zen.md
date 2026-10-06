# Session-scoped Superset cookie is unreadable from Firefox/Zen

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-08-27
- Related: `src/superset_cli/auth.py`, `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`, `README.md`, `docs/tickets/done/2026-08-27-auth-login-live-validation.md`, `docs/tickets/done/2026-08-27-auth-login-auto-fallback.md`

## Context

`auth login` reads cookies via `browser-cookie3`, which only reads cookies the
browser has written to `cookies.sqlite`. When Superset issues a **session-scoped**
`session` cookie (no `Expires`/`Max-Age`), Firefox-family browsers (including Zen)
keep it in memory and never write it to `cookies.sqlite`. The cookie is then
structurally invisible to the CLI in those browsers, even while the user is fully
logged in.

Proven on staging (no auth required):

```
$ curl -sS -D - -o /dev/null https://superset-staging.example.com/login/google \
    | grep -i set-cookie
set-cookie: session=<redacted>; Secure; HttpOnly; Path=/; SameSite=Lax
```

No `Expires`/`Max-Age` → session-scoped. Direct inspection of Zen's
`cookies.sqlite` showed zero `superset-staging` rows while logged in. Auto-fallback
and live validation (already shipped) correctly report the rejection, but the user
is left with no working path in Zen. Chrome works because it exposes session
cookies in its live cookie DB.

This is a real usability gap: the tool's primary auth path silently cannot serve
a common, correct Superset configuration.

## Definition of done

- [ ] Distinguish verified observations (no persisted cookie found, persisted cookie rejected, network failure, permission failure) from the possible explanation that a valid session exists only in browser memory; do not claim memory-only state can be detected from an empty SQLite result alone.
- [ ] Explain browser-specific recovery: one validated import attempt followed by a supported browser fallback or a clear blocked outcome, not repeated identical logout/login or quit/reopen instructions.
- [ ] Document when the existing `api` command performs its single automatic recovery attempt; do not broaden retries to sent mutations or treat every HTTP 403 as expired auth.
- [ ] Evaluate and pick at least one first-class remedy, e.g.:
      - a manual cookie/paste or `--cookie`/`--session` input path for when
        browser extraction cannot see the cookie;
      - reading Firefox/Zen `sessionstore` (session cookies) in addition to
        `cookies.sqlite`, if feasible and safe;
      - documenting Chrome as the supported browser for session-scoped setups.
- [ ] Tests cover missing and rejected persisted cookies, bounded recovery, network/permission failures, and any new input path without false claims of successful authentication.
- [ ] `README.md` and ADR 0008 document the limitation and the chosen remedy.

## Notes

Out of scope (explicitly rejected this session): WebDriver BiDi / remote-debugging
attach to a running browser — too specialized for the default workflow. Keep
`cookies.sqlite` extraction as the default; add a fallback rather than replacing it.

The 2026-10-06 workflow audit identified repeated ineffective authentication instructions. Existing live validation and automatic browser fallback are already implemented; first verify the installed CLI has those capabilities. Changing server cookie persistence or introducing secret-input paths requires separate explicit approval. Coordinate the companion-skill recovery instructions with `docs/tickets/todo/2026-10-06-refresh-companion-skill-recipes.md` and installation preflight with `docs/tickets/todo/2026-10-06-release-capability-preflight.md`.
