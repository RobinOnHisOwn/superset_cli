# Service-owned key operator prerequisite research

**Date:** 2026-10-08

## Goal

Record the source-verified operator fallback boundary without inventing cross-user REST endpoints or deploying an unverified privileged integration.

## Verified upstream behavior

Sources inspected at Superset 6.1.0 / FAB 5.2.2:

- [Superset security manager](https://github.com/apache/superset/blob/6.1.0/superset/security/manager.py) inherits FAB's concrete SQLA security manager and does not override the native key creation/revocation methods.
- [Native key API](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/api_key/api.py) creates only for `sm.current_user`. List/get/revoke are owner-scoped. Administrator privilege does not make this a cross-user HTTP API.
- [SQLA manager](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/manager.py) provides `create_api_key(user, name, scopes=None, expires_on=None)`, `get_api_key_by_uuid(uuid)`, `find_api_keys_for_user(user_id)`, and `revoke_api_key(uuid)`. Creation stores `user.id`, commits, and returns a UUID plus one-time plaintext `key`, not ownership metadata. The methods themselves do not enforce a CLI write flag or independent operator authorization/audit; they are application-side mechanisms, not evidence of a supported deployable extension contract.
- Creation failure returns `None` after caught exceptions; it must not authorize an automatic retry. Reconcile the operation marker and before-image before another mutation.
- Manager revocation sets `revoked_on` and commits; it does **not** set the stored `active` column false. [Model `is_active`](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/models.py) is false when `active` is false, `revoked_on` is present, or expiry has passed. Verify fresh stored revocation plus derived inactivity; never require an unsupported active-column change.
- Key validation commits usage bookkeeping and replaces `g.user`/`g._api_key_user`. Do not validate the issued runtime key inside the issuing/recovery context and accidentally change the operator identity. Acceptance requires a separate bounded read-only client/context.
- [Base security manager](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/manager.py) includes direct user roles and group roles. Builtin roles use regex permission/resource matching; raw stored role grants and even returned regex pairs are not proof of exactly four effective literal grants. Authentication synchronization and deployment overrides must also be inspected.

## Proposed operator fallback, not implemented or authorized

1. The deployment owner identifies its supported application-context runner and trusted operator authorization/audit mechanism. Do not add remote execution, shell access, or application imports to this CLI based on assumed deployment paths.
2. An owner-maintained runner must require literal per-invocation `--allow-write` before any mutation and a separate `--secret-output` for creation. Default output/errors remain secret-free. No credentials or one-time key in argv, files, environment copies, logs, or raw exceptions; the caller owns its receiver and pipeline checks.
3. Preflight actual versions, enabled/initialized key storage, prefix, verified server timezone/expiry, exact active service-user ID/username, role IDs/names, group roles, builtin/override rules and role synchronization. Reject incomplete evidence or drift rather than assuming direct grants prove effective least privilege. Never grant runtime key-management or Admin privileges to make issuance work.
4. Use a unique operation UUID/name and owner-scoped before-image. Invoke creation once with the already verified service-user object. From fresh stored state, verify returned UUID, exact `user_id`, name marker, expiry and derived activity before emission. Do not use the runtime credential for recovery or blindly retry unknown outcomes.
5. On failed validation/emission, revoke only the exactly reconciled newly issued service-owned key through the independent operator context. Verify fresh `revoked_on` and `is_active=false`; report missing/multiple candidates and failed/late compensation as unknown. Partial stdout may have escaped. Successful emission does not prove downstream storage.
6. Operator revocation must verify expected owner/UUID before its single manager call, reconcile afterward independently, and retain independent access even when the runtime key is rejected. On the authorized isolated instance, separately prove runtime rejection and positive/negative permission boundaries. No lifecycle grants on the runtime role.

## Unknown prerequisites and next action

No owning deployment repository, application-context execution contract, operator authorization/audit/recovery mechanism, verified clock, or authorized isolated target has been supplied. Therefore no privileged extension is selected, no operator runner is implemented here, and no live service-user/key mutation has occurred. Request those concrete inputs before implementing deployment-specific code. Existing CLI user/role CRUD and direct-grant commands remain reusable prerequisites, not end-to-end service-account administration.

## Verification

Version-pinned source inspection only; no live execution. Repository link checks must include this research and moved ticket links. Runtime integration, ownership/expiry/rejection, effective permission closure and independent recovery remain unverified.

## Decision follow-up

No durable decision change. ADRs [0023](../decisions/0023-environment-bound-api-keys.md), [0025](../decisions/0025-current-user-api-key-creation.md), and [0026](../decisions/0026-guarded-role-permissions.md) retain the current-user/operator and direct/effective permission boundaries. Select and record a deployment integration only after its missing contracts are verified.
