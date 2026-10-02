# 0011: Custom API calls with bounded automatic authentication

- Status: accepted
- Date: 2026-10-02

## Context

Agents need access to endpoints without dedicated CLI commands without extracting credentials or recreating CSRF handling. The user explicitly requested one automatic authentication attempt.

## Decision

Add `api INSTANCE PATH`, defaulting to GET and returning the full JSON response. Support repeated query parameters and JSON object bodies via inline text, stdin, or files. Only instance-relative `/api/v1/` paths are allowed; reject traversal and fragments and do not follow redirects for custom requests, session validation, or CSRF acquisition.

Validate saved authentication via `/api/v1/me/` before the custom request. Missing or rejected state triggers one existing browser-cookie import flow with live candidate validation. Network errors and permission failures do not trigger login. Existing commands retain their defaults. Automatic login does not launch a browser or create an SSO session.

POST, PUT, PATCH, and DELETE all require the shared per-invocation `--allow-write` guard before accessing browser profiles or the network, including potentially read-like POST endpoints. Obtain CSRF through the same no-redirect request path. Never retry a sent mutation or infer that a 403 means expired authentication.

## Consequences

Agents can use live OpenAPI discovery and arbitrary JSON endpoints safely without exporting authentication. Every invocation incurs a session validation request. Browser cookies may be inaccessible or stale; recovery then fails rather than looping. Multipart and binary responses remain the responsibility of dedicated commands.

## Alternatives considered

- Raw curl with exported cookies: exposes secrets and duplicates CSRF logic.
- Automatic login on all commands: changes existing defaults unnecessarily.
- Retrying every failed request: risks duplicate mutations and conflates permissions with authentication.

## References

- [Plan](../plans/2026-10-02-api-command.md)
- [Cookie authentication](0008-cookie-extraction-from-installed-browsers.md)
- [Write guard](0009-write-command-explicit-opt-in.md)
- `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_api.py`
