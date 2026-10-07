# Select an authorized service-account key provisioning integration

- Status: todo
- Blocker review (2026-10-07): no owning backend repository or deployed authorized cross-user interface was supplied. Native FAB remains current-user only; selecting a fictitious integration would violate the prerequisites. Supply the backend repository and its authorization/reconciliation contract before implementation. See [review plan](../../plans/2026-10-07-open-key-todos.md).
- Priority: high
- Type: research
- Created by: agent
- Created at: 2026-10-07
- Related: [research plan](../../plans/2026-10-07-api-key-lifecycle-ticket-research.md), [lifecycle](../in-progress/2026-10-07-api-key-lifecycle.md), [safe issuance](2026-10-07-secret-safe-key-issuance.md), [service role](2026-10-07-minimal-cache-service-role.md), [ADR 0023](../../decisions/0023-environment-bound-api-keys.md)

## Context

SAML and a minimal runtime role do not supply an authenticated service-user session for self-service key creation. FAB 5.2.2's `/api/v1/security/api_keys/` endpoints operate exclusively on the authenticated user. An administrator cannot target another user by adding `--user`.

This ticket records an external deployment prerequisite. Keep deployment details and implementations in the owning backend repository; public documentation must use neutral examples.

## Verified knowledge

- POST calls `sm.create_api_key(user=sm.current_user, ...)`; list filters by current user ID. Get/revoke check ownership and return 404 for a different owner.
- POST schema accepts required `name`, optional `scopes` string and optional ISO datetime `expires_on`. There is no user parameter.
- SQLA manager `create_api_key(user, name, scopes=None, expires_on=None)` generates and hashes the key, commits storage, and returns plaintext once. `revoke_api_key(uuid)` returns a boolean. Internal methods require an authorization wrapper before cross-user use.
- Registration requires `FAB_API_KEY_ENABLED`; prefix defaults to `sst_`. Verify installed versions, migration/key-table readiness, and configuration on the deployment.
- Stored scopes are not enforced by `validate_api_key`; they are not dataset authorization.

## Options to investigate

1. Prefer an existing authorized backend operational integration if available: call manager methods in Superset's application context with explicit target-user authorization.
2. Otherwise evaluate a narrow backend extension for provision/revoke/reconcile, separate from the runtime service role.
3. Self-service endpoints are usable only if an independently authorized service-user authentication path exists. Do not assume SAML provides one, add a password fallback, or impersonate a user through CLI flags.

## Definition of done

- [ ] Inspect the actual deployment and existing operational integration; document verified capabilities and missing prerequisites, without secrets or real instance details.
- [ ] Select the smallest authorized option and record its trust boundary in a backend ADR. Specify who may issue/revoke for which users; do not grant runtime callers provisioning privileges.
- [ ] Define request/response metadata, key UUID/owner reporting, expiry policy, audit records without secret values, and a secret-safe delivery channel to the issuance workflow.
- [ ] Provide independently authenticated revocation and metadata reconciliation for failed delivery, lost responses, and partially completed operations. A timed-out create must not be blindly repeated.
- [ ] Verify target user existence/activity, version/configuration and storage prerequisites before issuance; test unauthorized cross-user requests and invalid targets.
- [ ] Verify effective revocation from stored state and, where authorized, key rejection. Do not rely on native revoke HTTP 200 alone.
- [ ] Hand the verified integration contract to the safe-issuance ticket. No CLI `--user` promise until such an integration exists.

## Sources

- [FAB API](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/api_key/api.py)
- [FAB schema](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/api_key/schema.py)
- [FAB SQLA manager](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/manager.py)

## Decision follow-up

Decision record update required: backend provisioning authorization and recovery design in the owning repository; review ADR 0023 before any CLI issuance support.
