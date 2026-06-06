# Design: direct JWT auth support

## Status

Research only. No code changes. This document supersedes the earlier speculative version with concrete evidence from FAB and Superset source as of 2026-06-06.

## Evidence

### Endpoints

The login and refresh endpoints come from Flask-AppBuilder (`flask_appbuilder/security/api.py`), not from Superset itself. They are present in **all FAB ≥ 4.x** versions and therefore present in every supported Superset release (4.x → 6.1.x and master).

- **`POST /api/v1/security/login`** — body `{username, password, provider, refresh}`.
  - Response 200 → `{"access_token": "...", "refresh_token": "..."}` (no `result` wrapper).
  - `provider` enum is **`db` or `ldap`** only. From `flask_appbuilder/const.py`:
    ```python
    API_SECURITY_PROVIDER_DB = "db"
    API_SECURITY_PROVIDER_LDAP = "ldap"
    ```
    Login dispatches to `auth_user_db` or `auth_user_ldap`. **OAuth, OIDC, SAML, and REMOTE_USER are not supported by this endpoint.**
  - `refresh: true` is required to receive a refresh token.
  - Response 401 on bad credentials, 400 on malformed JSON.

- **`POST /api/v1/security/refresh`** — requires `Authorization: Bearer <refresh_token>` (uses `@jwt_required(refresh=True)`).
  - Response 200 → `{"access_token": "..."}` (no refresh-token rotation; the original refresh token stays valid).
  - Response 401 on missing/expired refresh token.

### Token format

- Both tokens are JWTs minted by `flask-jwt-extended`. Superset 6.1.0 pins `PyJWT>=2.4.0, <3.0`.
- Expiry is controlled by `JWT_ACCESS_TOKEN_EXPIRES` and `JWT_REFRESH_TOKEN_EXPIRES` in the Flask config (Superset defaults inherit from FAB; common deployments set short access TTLs and longer refresh TTLs).
- The token payload's `exp` claim is parseable client-side without verifying the signature, which is how a CLI can report expiry without holding the signing secret.

### CSRF

- The login and refresh endpoints are unprotected by CSRF (CSRF gates the browser-MVC routes). A JSON POST without a CSRF token is accepted.
- The CSRF token endpoint `/api/v1/security/csrf_token/` (confirmed in `superset/security/api.py`) is for browser-session callers. **JWT bearer auth does not need it.**

### Endpoint coverage

- The `@protect()` decorator in `flask_appbuilder/security/decorators.py` calls `verify_jwt_in_request()` whenever a request is not a public resource, not an API key, and not a browser session. That means every CLI read endpoint already covered (`/api/v1/dashboard/`, `/api/v1/chart/`, etc.) accepts a Bearer access token transparently.

## Supported scenarios

JWT auth is worth supporting in this CLI only when **all** of these are true for a given Superset instance:

1. `AUTH_TYPE` includes `AUTH_DB` or `AUTH_LDAP`. From `flask_appbuilder/const.py`, those are types 1 and 2.
2. A local user (DB-backed) or LDAP-backed user exists with credentials the agent is allowed to store in environment variables.
3. The instance accepts bearer tokens on the read endpoints the CLI uses (verified above for the default `@protect()` decorator).

## Non-goals

- Logging in with OAuth/OIDC/SAML/REMOTE_USER credentials. The login endpoint explicitly does not dispatch to those backends. Documented as a hard non-goal.
- Storing passwords in the config file. Secrets live in env vars only.
- Replacing browser-session auth. JWT is an alternative, not a replacement; the two coexist per instance.

## Credential inputs

- New config fields under `instances[].auth`:
  - `mode: cookie | jwt` (default `cookie`).
  - `jwt.username_env: SUPERSET_USERNAME_PROD`
  - `jwt.password_env: SUPERSET_PASSWORD_PROD`
  - `jwt.provider: "db" | "ldap"` (default `"db"`; the field exists to make the assumption explicit and to refuse other values).
- The CLI reads `username` and `password` from those env vars at login time.
- No on-disk storage of the password itself.

## Token lifecycle

- `auth jwt login <instance>` calls `POST /api/v1/security/login` with `refresh: true`, then persists access + refresh tokens at `<state_dir>/<instance>/jwt-state.json` with file mode `0600`.
- `auth jwt refresh <instance>` calls `POST /api/v1/security/refresh` using the saved refresh token and overwrites the access token. The refresh token is left untouched (Superset's refresh does not rotate it).
- Each API call attaches `Authorization: Bearer <access_token>`.
- On a 401 response with `mode=jwt`, the client attempts one refresh-then-retry. If the refresh also returns 401 (refresh token expired), surface a clean `AuthExpiredError` directing the user to `auth jwt login`.
- `auth jwt logout <instance>` deletes the saved JWT state file.
- `auth status` (existing) gains optional fields when `mode=jwt`: `access_token_exp` and `refresh_token_exp`, derived by base64-decoding the JWT payload (no signature verification). Token values themselves are never printed.

## Interaction with other auth modes

- Cookie and JWT state live in different files (`storage-state.json` vs `jwt-state.json`); they do not collide. The active mode is resolved per call from the instance config.
- If API-key mode is added later (see [[api-key-auth-design]]), precedence is: `--auth-mode` CLI flag → instance config `auth.mode` → fallback (cookie if storage state exists, else error).

## Secret handling

- Username and password are read from env vars only.
- Tokens persisted on disk at file mode `0600`.
- Token values must never appear in `--json` output or human-readable messages. Status output reveals only `exp` timestamps.

## Tests (for the eventual implementation ticket)

- Login: env vars resolved, POST body shape is `{"username", "password", "provider", "refresh": true}`, response tokens persisted with `0600` perms, response top-level keys handled (no `result` wrapper).
- Refresh: `Authorization: Bearer <refresh_token>` sent, new access token persisted, saved refresh token retained.
- 401 retry: one refresh attempt, then surface auth-expired error pointing at `auth jwt login`.
- Provider not in `{db, ldap}`: refuse before making the network call with a clear error.
- JSON output never contains a token value; only `exp` timestamps.
- `auth jwt logout` deletes the state file.

## Recommendation

This is implementable today against any Superset version the CLI is likely to encounter. It is genuinely useful for headless / agent contexts where the browser-login flow is awkward (CI, server-side automation, scripted smoke tests).

The implementation requires expanding the auth surface beyond the current browser-session-only model. Per `CLAUDE.md`, that needs explicit user authorization. The follow-up ticket `2026-06-06-jwt-auth-support.md` already exists in `todo/`; it should be picked up only after that authorization.

## Decision follow-up

Decision record update required when implementation is approved: add an ADR under `docs/decisions/` that records:
- The `provider in {db, ldap}` constraint and why other auth backends are out of scope.
- The env-var-only secret rule.
- The 0600-mode token persistence.
- The single-attempt refresh-then-retry policy on 401.

These are the assumptions most likely to cause confusion or security regressions later.
