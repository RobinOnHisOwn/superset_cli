# 0018: Per-instance JWT authentication

- Status: accepted
- Date: 2026-10-06
- Related: [continuation plan](../plans/2026-10-06-autonomous-todos-continuation.md), [JWT design](../plans/2026-06-06-jwt-auth-design.md), `src/superset_cli/jwt_auth.py`, `tests/test_jwt_auth.py`

## Context

DB/LDAP deployments can authenticate directly through FAB login/refresh endpoints. Browser-only SSO deployments cannot use that flow. Browser state and bearer tokens must not be confused, and authentication recovery must never replay a sent mutation.

## Decision

Keep cookie auth as the default and select JWT explicitly per instance. Accept credential environment-variable names, never persist passwords or password values in arguments. Save tokens privately in a separate `jwt-state.json`; browser state is preserved. Same-directory private transactional staging and atomic replacement preserve old state on replacement failure; normal failure removes staging files. Login/refresh/logout and status provide the lifecycle. Expiry decoding is unverified and display-only.

Reject malformed/non-object token responses and invalid bearer syntax without echoing values. Require HTTPS for login/refresh/API, with HTTP restricted to loopback development; reject embedded URL credentials. Disable diagnostic locals explicitly so unexpected exceptions cannot dump credentials. Updating an instance URL preserves existing auth selection/bindings rather than silently switching back to cookies.

JWT requests do not import browser cookies. On GET 401, refresh and retry once; on sent write failures, never retry. Report permission/network failures as such. Retain CSRF for modifying APIs: Superset 6.1.0 `BaseSupersetApiMixin.csrf_exempt = False`, while FAB login/refresh use CSRF-exempt BaseApi. Correct the previous design's no-CSRF assumption.

## Consequences

Direct DB/LDAP credentials and deployment support are prerequisites. Logout leaves browser state intact; switching modes is explicit. Refresh before manually repeating a mutation and inspect the first outcome. No real deployment's JWT login or refresh was exercised during implementation.

## Alternatives considered

### Browser cookies only

Remain appropriate for OAuth/OIDC/SAML/REMOTE_USER, but do not support direct credential-based automation.

### Retry any request after refresh

Could duplicate a mutation whose response was lost or rejected after effects occurred; GET-only bounded retries are safer.
