# Determine supported service-user key administration or document operator fallback

- Status: todo
- Priority: high
- Type: research
- Created by: agent
- Created at: 2026-10-07
- Related: [service role](2026-10-07-minimal-cache-service-role.md), [secret output](2026-10-07-secret-safe-key-issuance.md), [acceptance](2026-10-08-service-account-isolated-acceptance.md), [current-user lifecycle](../in-progress/2026-10-07-api-key-lifecycle.md), [ADR 0023](../../decisions/0023-environment-bound-api-keys.md)

## Context

Automation needs a dedicated `svc_cache_invalidator` identity, not a human administrator's key. Reuse existing authentication, user/role CRUD, invalidation, and current-user key list/get/revoke.

Verified baseline supplied with the task: Superset 6.1.0 / Flask-AppBuilder 5.2.2 native key creation binds to the authenticated user; list/get/revoke are owner-only, including for administrators. A key name or CLI `--user` option cannot change ownership. The security manager supports `create_api_key(user=service_user, name="cache-invalidation")` and `revoke_api_key(key_uuid)`; this is not evidence of a supported privileged REST endpoint.

Unknown: whether a supported, separately authorized backend integration exists in the target deployment. No live target or mutation authorization is provided by this ticket.

## Definition of done

- [ ] Research version-pinned upstream documentation/source and the owning deployment's integration contract; record evidence distinguishing supported extension points from internal methods.
- [ ] Choose a supported privileged issuance/revocation integration only if its ownership, authorization, audit, and reconciliation contracts are verified. Keep backend implementation in its owning repository.
- [ ] If none exists, document operator-side bootstrap and revocation using the security manager in an authorized application context. Do not invent REST operations or promise cross-user native CLI key management.
- [ ] Document preflight checks for exact user identity/activity, complete role permissions, key ownership (for existing keys), versions, API-key enablement/storage, and independent operator recovery access. Reject unexpected privilege drift before any mutation; verify newly issued ownership before delivery.
- [ ] Require literal per-invocation `--allow-write` for every remote mutation in the selected CLI/operator workflow; no config/env/prompt override. Runtime identity receives no key-management permissions.
- [ ] Specify non-secret owner/UUID metadata and reconciliation for lost responses. Never automatically retry a sent mutation; uncertain outcomes are non-success with explicit operator guidance.
- [ ] Prove operator revocation without using the runtime credential or granting it lifecycle permissions; verify stored revocation and, on the authorized isolated instance, credential rejection.
- [ ] Hand the verified integration or operator fallback to the secret-output and acceptance tickets. Write an implementation plan before code changes and record any durable authorization/recovery decision.

## Notes

Scope excludes 1Password integration and dataset allowlists; both belong in the shell/caller. Public documentation uses neutral examples and never real credentials or instance data.

Sources to verify: [FAB 5.2.2 API](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/api_key/api.py), [schemas](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/api_key/schema.py), [security manager](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/manager.py).
