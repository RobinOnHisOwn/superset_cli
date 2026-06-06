# Research: guest-token auth support

## Status

Research only. No code changes.

## What guest tokens are

Superset issues short-lived JWT-shaped "guest tokens" via `POST /api/v1/security/guest_token/`. The token grants embedding clients limited access to **specific** dashboard resources and is intended to be passed to the Superset embed SDK in a host page. The token is scoped to:

- A specific user descriptor (chosen by the issuer; not a real Superset user).
- A specific set of resources (typically `[{type: "dashboard", id: <id>}]`).
- Optional row-level-security rules to apply.

The token is **not** a general-purpose API credential. The endpoints embedded clients hit do not equal the full read surface this CLI uses.

## Valid use cases for this CLI

If guest tokens were added, the realistic uses are:

1. **Validation aid for embedded-dashboard ticket holders.** After configuring an embedded dashboard, an operator might want to issue a guest token from the CLI to verify the embed configuration without spinning up a host page. This is the strongest candidate.
2. **Smoke-testing a dashboard's RLS configuration** by varying the `rls` field in the request and observing which charts a token can fetch.

Use cases that are **not** valid:

- Replacing normal cookie/JWT auth for the CLI's existing read commands. Guest tokens cannot call `/api/v1/dashboard/`, `/api/v1/chart/`, etc.
- Long-lived "service token" workflows. Guest tokens are deliberately short-lived.

## Distinction from general API auth

| Aspect | Cookie / JWT auth | Guest token |
| --- | --- | --- |
| Scope | Full user permissions | A single embed grant |
| Endpoints reachable | All read endpoints used by the CLI | Embed-only data fetch endpoints |
| Lifetime | Hours to days (session) | Minutes (issuer-controlled) |
| Persistence | Saved to disk | Should not be persisted |

## Prerequisites and constraints

- The Superset instance must have `FEATURE_FLAGS["EMBEDDED_SUPERSET"]` enabled. Without it, the endpoint returns a feature-flag error.
- Issuing a guest token requires a normal authenticated session that already has the right permissions, so this would not replace the existing cookie/JWT flow; it would build on it.
- CSRF is enforced for `POST` on this endpoint when CSRF protection is on; the CLI would need to first `GET /api/v1/security/csrf_token/` and include the header on the issue request.

## Recommendation

**Defer.** Add no CLI surface until there is a concrete embedded-dashboard verification workflow that requires it. If we add anything later, it should be a single read-style command (`auth guest-token issue`) that prints the token to stdout (with strong warnings about its sensitivity) and never persists it.

If deferred, this ticket can be closed as research-only. A new ticket should be opened only when a real embed workflow surfaces a need.

## Decision follow-up

No durable decision change. The research is captured here; no decision record is needed unless implementation begins.
