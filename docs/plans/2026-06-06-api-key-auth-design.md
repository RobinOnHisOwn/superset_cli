# Design: version-gated API-key auth support

## Status

Updated 2026-10-06 after rechecking concrete inheritance. The original conclusion that Superset 6.1.0 necessarily reaches FAB's abstract `validate_api_key` was incorrect. Implementation is tracked by [the continuation plan](2026-10-06-remaining-open-todos.md) and [ADR 0023](../decisions/0023-environment-bound-api-keys.md).

## Verified evidence

- [Superset 6.1.0 release](https://github.com/apache/superset/releases/tag/6.1.0) is stable. Its [pyproject.toml](https://github.com/apache/superset/blob/6.1.0/pyproject.toml) permits `flask-appbuilder>=5.0.2,<6`.
- [SupersetSecurityManager](https://github.com/apache/superset/blob/6.1.0/superset/security/manager.py) inherits `flask_appbuilder.security.sqla.manager.SecurityManager`, not just the abstract base.
- [FAB 5.2.2's concrete SQLA manager](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/manager.py) implements `validate_api_key`, key storage, hash verification, active/expiry checks, authenticated-user setup, and registration of the API-key blueprint when `FAB_API_KEY_ENABLED` is true.
- [FAB 5.2.2's protect decorator](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/decorators.py) checks API keys before JWT when enabled. Recognized prefixes default to `sst_`; custom `FAB_API_KEY_PREFIXES` are deployment settings.
- Superset's [Next security documentation](https://superset.apache.org/admin-docs/security/) documents Bearer API keys, but is unreleased documentation and does not alone establish a stable release's capabilities.

## Target-version contract

The verified source combination is **Superset 6.1.0 with FAB 5.2.2**, `FAB_API_KEY_ENABLED=True`, compatible initialized key storage, an active issued key, and a matching prefix. Superset 6.1.0's broad FAB range is not a guarantee that every installation has API-key support. No promise is made for older FAB, arbitrary Superset releases, or an unverified deployment. CLI code does not create keys, change server flags, initialize storage, or upgrade dependencies.

A real target deployment and credential were not used in this task. The binding command requires a successful authenticated read through the actual key before saving local configuration; mocks verify client behavior, not live deployment availability.

## CLI contract

- Explicit per-instance `auth.mode: api_key` and `auth.api_key: {env: EXAMPLE_SUPERSET_API_KEY, prefix: sst_}`.
- `auth api-key set INSTANCE --env NAME [--prefix PREFIX]` reads the environment value, rejects malformed/missing credentials, and validates `GET /api/v1/me/` without redirects before saving only the binding.
- `auth api-key clear INSTANCE` returns to cookie mode without deleting cookie or JWT state.
- All API-backed workflows select the same shared client factory. API-key mode needs no browser auth file, never imports cookies, never refreshes JWT, and never replays a sent mutation.
- HTTPS is required except loopback HTTP development; embedded URL credentials are rejected. CSRF and literal `--allow-write` remain enforced.
- `auth status` reports credential availability, not live acceptance. `auth validate` performs the read check. API keys are not browser state and cannot be exported to Playwright.

## Secret handling

Never persist or print keys. Only environment variable names and prefixes enter config/output. Each invocation rereads the environment, allowing rotation without rewriting config. No API-key issue/revoke endpoint is added. Existing cookie/JWT defaults and JSON shapes remain unchanged.

## Alternatives

Continuing to block all API-key support based on the abstract superclass would preserve an incorrect assumption. Blindly treating any Bearer token or Superset version as supported would guess through real deployment requirements. An explicit, validated environment binding uses the verified protocol while leaving unsupported deployments safely rejected.

## Decision follow-up

Decision record update required: [ADR 0023](../decisions/0023-environment-bound-api-keys.md).
