# 0023: Environment-bound API keys on verified server capabilities

- Status: accepted
- Date: 2026-10-06
- Related: [corrected research](../plans/2026-06-06-api-key-auth-design.md), [continuation](../plans/2026-10-06-remaining-open-todos.md), `src/superset_cli/api_key_auth.py`, `tests/test_api_key_auth.py`

## Context

API-key authentication is version/configuration dependent. Earlier research examined FAB's abstract manager but missed Superset's inheritance of FAB's concrete SQLA manager. Superset 6.1.0 permits FAB 5.2.2, which implements API-key verification and blueprint registration. This establishes a source-verified combination, not support on every 6.1.0 deployment. No live key or deployment was exercised.

## Decision

Add explicit per-instance API-key mode with only an environment-variable binding and configured prefix (default `sst_`). `auth api-key set` requires syntactically valid credentials and successful read-only `/api/v1/me/` authentication before saving the binding. Reject redirects and preserve old config on failed validation. `clear` returns to cookie mode and preserves existing cookie/JWT files. Explicit `set` replaces prior auth bindings, and `clear` does not restore previous JWT bindings or mode; switching back requires explicit JWT configuration.

Use a shared CLI client factory for every API-backed handler. Read the key afresh per invocation, enforce bearer syntax and prefix, require HTTPS except loopback HTTP, and reject embedded URL credentials. No auth file is needed or created. Never persist/log the key, fall back to cookies/JWT, retry a sent mutation, issue keys, or change server flags/dependencies. Existing CSRF handling, HTTP timeouts, and literal per-invocation `--allow-write` apply unchanged.

Document the verified combination as Superset 6.1.0 + FAB 5.2.2 with `FAB_API_KEY_ENABLED=True`, initialized key storage, matching prefix, active issued key, and sufficient RBAC. Do not infer capability from the Superset version alone or from Next documentation. CLI binding validation, not a hardcoded version guess, determines acceptance on a target deployment.

Status reports local credential availability without implying current server acceptance; `auth validate` performs the live read. API keys cannot substitute for browser state in rendering/export recipes.

### Current-user lifecycle extension (2026-10-07)

Under the [autonomous Todo implementation plan](../plans/2026-10-07-open-key-todos.md),
permit current-user `auth api-key list/get/revoke` through pinned FAB 5.2.2 native
endpoints. No cross-user targeting or creation is included. Reuse shared client,
authentication and CSRF; native list is unpaginated. Require literal
`--allow-write` before revocation credential/network access, and validate UUID
arguments before access. Permissions are `can_list`, `can_get`, `can_revoke` on
`ApiKey`; revocation additionally needs get/CSRF access.

Output is metadata-only, projected onto native response fields with scalar
values; omit plaintext keys, hashes, extra fields and all server error bodies.
JSON is `{result: [...]}` for list and `{result: {...}}` for get/revoke. Revocation
preflights ownership/read access, sends DELETE exactly once, then requires
matching UUID, `active=false` and a parseable revocation timestamp on GET. HTTP
200 alone is not proof. Failed or unavailable read-back, self-revocation and
ambiguous transport outcomes are non-success, with UUID-only recovery guidance.
Use an independent authorized same-user credential to reconcile before retrying.
Stored-state verification does not claim separately observed key rejection.
The runtime cache role receives no lifecycle grants. Creation remains blocked
on a verified secret-delivery and independently authenticated recovery contract.
Tests: `tests/test_api_key_lifecycle.py`.

## Consequences

Operators can use issued keys without browser-cookie extraction or local secret files. The environment must be populated on each invocation. Server-side key creation and rollout remain operator responsibilities; current-user revocation now has an explicitly guarded CLI path. GET authentication may update server-side key usage bookkeeping; the CLI performs key-management mutation only through explicit guarded revocation.

## Alternatives considered

### Persist keys or accept literal key arguments

Rejected: exposes secrets in configuration, shell history, process arguments, or logs.

### Treat every Superset 6.1.0 installation as supported

Rejected: its FAB dependency range includes versions predating API keys and server enablement/storage vary.

### Block forever because Superset has no direct override

Rejected after source verification: the concrete inherited implementation exists. Requiring successful credential validation before binding handles the actual deployment prerequisite without inventing availability.
