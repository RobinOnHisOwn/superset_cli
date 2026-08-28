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
$ curl -sS -D - -o /dev/null https://superset-staging.jobvalley.tech/login/google \
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

- [ ] `auth login` detects the "matching cookie exists in browser but is
      session-scoped / not persisted" situation and explains it specifically,
      including the concrete fixes (use Chrome; or make the Superset session
      cookie permanent), rather than a generic "rejected" message.
- [ ] Evaluate and pick at least one first-class remedy, e.g.:
      - a manual cookie/paste or `--cookie`/`--session` input path for when
        browser extraction cannot see the cookie;
      - reading Firefox/Zen `sessionstore` (session cookies) in addition to
        `cookies.sqlite`, if feasible and safe;
      - documenting Chrome as the supported browser for session-scoped setups.
- [ ] Tests cover the session-scoped detection/messaging and any new input path.
- [ ] `README.md` and ADR 0008 document the limitation and the chosen remedy.

## Notes

Out of scope (explicitly rejected this session): WebDriver BiDi / remote-debugging
attach to a running browser — too specialized for the default workflow. Keep
`cookies.sqlite` extraction as the default; add a fallback rather than replacing it.
