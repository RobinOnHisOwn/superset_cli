# Design: version-gated API-key auth support

## Status

Research only. No code changes. This document supersedes the earlier speculative version with concrete evidence from FAB and Superset source as of 2026-06-06.

## Evidence

### FAB

API-key authentication shipped in **Flask-AppBuilder 5.2.0** (release notes, FAB `CHANGELOG.rst`):

> feat: add API key authentication support (#2431) [Amin Ghadersohi]

Latest FAB at time of writing: 5.2.1.

The implementation is in `flask_appbuilder/security/decorators.py` (`protect()` decorator) and `flask_appbuilder/security/manager.py` (`BaseSecurityManager.extract_api_key_from_request` and `validate_api_key`). The request shape is:

- Header: `Authorization: Bearer <api_key>`.
- The token must start with one of the prefixes in `FAB_API_KEY_PREFIXES` (default `["sst_"]`). Tokens without a recognized prefix fall through to JWT validation.
- The endpoint must be gated by `@protect()` (every `@expose` on `BaseApi` subclasses is).
- The feature is enabled by `FAB_API_KEY_ENABLED=True` in Flask config. With the flag off, the API-key path in `protect()` is skipped entirely.

`BaseSecurityManager.validate_api_key` is `NotImplementedError` — concrete subclasses (Superset's `SupersetSecurityManager`) must implement storage and verification.

### Superset version matrix

| Superset version | FAB pin | API-key wiring in Superset SM | Practical availability |
| --- | --- | --- | --- |
| 4.1.4 (and earlier 4.x) | `flask-appbuilder==4.5.0` | n/a (FAB lacks the feature) | **No** |
| 6.1.0 (latest stable, May 2026) | `flask-appbuilder>=5.0.2, <6` | None — `grep ApiKey\|FAB_API_KEY` in `superset/security/manager.py` returns zero hits | **No** in practice |
| master / future 7.x | `flask-appbuilder>=5.2.1, <6.0.0` | Yes — `ApiKey` view, `can_list/can_create/can_get/can_revoke` perms wired under `FAB_API_KEY_ENABLED=True` | **Yes** when flag is on |

Note on 6.1.0: the pin `>=5.0.2` *allows* FAB 5.2.x to be installed, and FAB's `protect()` decorator and `extract_api_key_from_request` are then present. But because Superset 6.1.0's security manager subclass does not override `validate_api_key`, calls will hit `NotImplementedError`. The feature is effectively non-functional on 6.1.0 even with the flag enabled and a compatible FAB.

### Token format (from FAB master)

```python
auth_header = request.headers.get("Authorization", "")
if not auth_header.lower().startswith("bearer "):
    return None
token = auth_header[7:].strip()
prefixes = current_app.config.get("FAB_API_KEY_PREFIXES", ["sst_"])
for prefix in prefixes:
    if token.startswith(prefix):
        return token
return None
```

So a CLI request looks like `Authorization: Bearer sst_<random>` (or any prefix the operator configured).

### Not API keys

The doc page **"Receive personal access tokens from OAuth2"** at `GET /api/v1/database/oauth2/` is unrelated. It's a callback endpoint for receiving OAuth2 tokens from *backing databases* (e.g. Snowflake OAuth) for per-user database authorization. The "personal access token" wording refers to the database's PAT, not a Superset API key. This endpoint must not be confused with Superset API-key auth.

## Target-version assumption

This CLI documents compatibility with current stable self-hosted Apache Superset OSS. Today that's 6.1.x. Under that constraint, API-key auth is **not available** in any released form.

API-key auth becomes available when Superset 7.0 (or whichever release first ships the security-manager wiring currently on `master`) reaches a stable tag.

## Provisional CLI contract (only valid once API keys are available)

- Config additions:
  - `instances[].auth.mode: cookie | jwt | api_key` (default `cookie`).
  - `instances[].auth.api_key_env: SUPERSET_API_KEY_PROD` — name of an env var holding the secret. The secret is never persisted in the config file.
- New subcommands:
  - `auth api-key set <instance> --env <env-var-name>` registers the env-var binding.
  - `auth api-key clear <instance>` removes it.
- Client behavior:
  - When `mode == api_key`, the client reads the secret from the named env var at call time and sends `Authorization: Bearer <key>` instead of the cookie header.
  - Missing env var → clean CLI error directing the user to set it before retrying.
  - The CLI does not call FAB's `ApiKey` issue/revoke endpoints — operators issue keys via the Superset UI or admin tooling, then provide them to the CLI through env vars only.

## Secret handling

- Secrets are read from environment only. Storing keys in the config file is out of scope and remains forbidden.
- Logging and `--json` outputs must never include the secret value. JSON shape includes only `mode` and `api_key_env` name.

## Auth-mode selection precedence

When implemented, mode resolution should match the precedence proposed in [[default-instance-selection]]:

1. `--auth-mode` CLI flag (per-invocation override).
2. `instances[].auth.mode` in config.
3. Implicit fallback: `cookie` if storage state exists for the instance, otherwise error with a clear message.

## Prerequisites before picking up the implementation ticket

The follow-up ticket `2026-06-06-api-key-auth-support.md` (already in `todo/`) is gated on **all** of these being independently verified against the target instance's actual release at the time of implementation:

1. The Superset release in use lists API-key auth in its release notes / `CHANGELOG/*.md` as a stable feature (not behind an experimental feature flag other than `FAB_API_KEY_ENABLED`).
2. `superset/security/manager.py` for that release overrides `validate_api_key`, `extract_api_key_from_request`, and the create/revoke helpers (or inherits a working implementation from FAB's concrete SQLA subclass).
3. The `Authorization: Bearer <key>` header successfully authenticates a request to the read endpoints this CLI uses (`/api/v1/dashboard/`, `/api/v1/chart/`, etc.) on the target instance.

Until those three checks succeed for a specific release, API-key auth must be treated as **not available** for this CLI.

## Recommendation

Defer implementation. The current CLI compatibility target (Superset 6.1.x) does not support API-key auth in any usable form. JWT auth ([[jwt-auth-design]]) covers the same "headless credentials" use case today and is the right next step if the user wants to expand beyond browser sessions.

Revisit this ticket once Superset 7.x stable ships with the API-key wiring observed on `master`.

## Decision follow-up

No durable decision change yet. A decision record should be added only when implementation is approved; it should record:
- The verified Superset version and release date.
- The `FAB_API_KEY_ENABLED=True` requirement on the server.
- The chosen `Authorization: Bearer <prefix>...` header format and which `FAB_API_KEY_PREFIXES` value is assumed.
- The env-var-only secret rule.
