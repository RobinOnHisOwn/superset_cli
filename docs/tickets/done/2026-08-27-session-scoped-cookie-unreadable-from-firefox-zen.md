# Explain unavailable persisted cookies in Firefox/Zen

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-08-27
- Related: `src/superset_cli/auth.py`, `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`, `README.md`, `docs/tickets/done/2026-08-27-auth-login-auto-fallback.md`

## Context

Cookie extraction can only import cookies exposed by the supported browser loaders. An empty persisted-cookie result does not prove that no valid browser session exists. A session-only cookie may remain in browser memory, depending on browser/version/configuration. Do not claim that memory-only cookies can be detected from an empty SQLite result.

The source ticket contained committed conflict markers and non-example hostnames; this version resolves those conflicts while retaining the evidence-based requirements.

## Definition of done

- [x] Distinguish no persisted matching cookies, persisted cookies rejected by Superset, network failure, and permission failure.
- [x] Explain that Firefox/Zen may retain a session only in memory; describe it as a possible explanation, not a detected fact.
- [x] Document a supported-browser fallback after an explicit unavailable-cookie outcome; do not recommend repeated identical logout/login or browser restart loops.
- [x] Document the existing `api` command's single bounded browser-cookie recovery attempt; do not retry a sent mutation or treat every HTTP 403 as expired authentication.
- [x] Choose a first-class remedy without introducing a secret-input path or changing server cookie persistence: document validated import from a supported browser such as Chrome when its session is accessible.
- [x] Test missing and rejected persisted cookies, bounded recovery, and network/permission failures.
- [x] Update README and ADR 0008.

## Completion evidence

Diagnostics separate inaccessible persisted cookies from rejected cookies and network/permission failures. Memory-only state is described as possible, not detected. README/ADR 0008 document accessible supported-browser import or blocked outcome, no restart/login loops, and bounded API recovery without mutation replay. See [continuation evidence](../../plans/2026-10-06-autonomous-todos-continuation.md).

## Notes

Keep cookie extraction as the default. Manual secret entry, sessionstore parsing, and remote browser debugging are deferred until separately justified. Coordinate broader capability-preflight and companion-skill work with their existing tickets.
