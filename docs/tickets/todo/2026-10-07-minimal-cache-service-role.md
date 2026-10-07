# Provision and verify the minimal CLI-compatible cache service role

- Status: todo
- Priority: high
- Type: research
- Created by: agent
- Created at: 2026-10-07
- Related: [provisioning integration](2026-10-07-service-key-provisioning-integration.md), [caller allowlist](2026-10-07-cache-caller-dataset-allowlist.md), [live cache acceptance](../in-progress/2026-10-07-targeted-cache-invalidation.md), [ADR 0024](../../decisions/0024-targeted-cache-controls.md), `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

Provision the runtime service identity in the owning deployment repository, reusing existing role/user CRUD instead of a custom cache HTTP client. Runtime invalidation and privileged key provisioning are separate duties.

## Source-verified required permissions

| Permission | Resource | Reason |
| --- | --- | --- |
| can_invalidate | CacheRestApi | POST `/api/v1/cachekey/invalidate` |
| can_read | SecurityRestApi | GET `/api/v1/security/csrf_token/` for existing CSRF handling |
| can_read | CurrentUserRestApi | GET `/api/v1/me/` for binding/auth validation |
| can_get | OpenApi | GET `/api/v1/_openapi` for invalidation-schema validation |

Superset 6.1.0/FAB 5.2.2 source verifies these method/resource names. Effective deployment permissions, endpoint registration, key storage readiness, and cache backend behavior have not been inspected live.

Do not add `ApiKey` lifecycle, role/user administration, chart/dataset reads, SQL execution, or broad Admin/Gamma permissions to this runtime role. Provisioning uses a separate authorized identity. These four grants allow targeted requests but do not isolate authorized dataset IDs server-side.

## Definition of done

- [ ] Identify the owning deployment and obtain explicit authorization for role/user writes and test invalidation; this research ticket itself authorizes no live mutation.
- [ ] Verify installed Superset/FAB versions, enabled/initialized API-key storage, configured prefix, SAML role synchronization behavior, and permission-view registrations. Resolve permission IDs from live metadata; never guess IDs.
- [ ] Reuse existing `security role-create/role-update` and `user-create/user-update` with literal `--allow-write` and verified payload schemas. If permission discovery needs an existing generic API read, reuse it; no new transport.
- [ ] Assign exactly the four grants to the runtime role. Inspect effective user permissions from all direct/group/inherited roles and ensure SAML synchronization cannot silently broaden or erase the intended assignment.
- [ ] Provision the service key using the separately authorized backend integration and verified 1Password workflow; do not give the runtime role lifecycle permissions to bootstrap itself.
- [ ] Verify `/me/`, CSRF and OpenAPI reads with the runtime credential. Explicitly authorized isolated invalidation must succeed through the existing CLI, while administration and key lifecycle requests are denied.
- [ ] Verify tracked keys, `STORE_CACHE_KEYS_IN_METADATA_DB=True`, cache/data-cache alignment and normal non-forced freshness using the existing live-acceptance ticket. HTTP acceptance alone is not eviction proof.
- [ ] Record exact commands and redacted outcomes in the owning repository; use neutral public examples. Document rollback/revocation procedures and remaining unverified conditions.

## Sources

- [CacheRestApi](https://github.com/apache/superset/blob/6.1.0/superset/cachekeys/api.py)
- [SecurityRestApi](https://github.com/apache/superset/blob/6.1.0/superset/security/api.py)
- [CurrentUserRestApi](https://github.com/apache/superset/blob/6.1.0/superset/views/users/api.py)
- [FAB OpenApi](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/api/manager.py)
- [FAB API permissions](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/api/__init__.py)

## Decision follow-up

Decision record update required in the deployment repository: separation of provisioning/runtime identities and least-privilege role reconciliation. No CLI transport or permission expansion is needed for this task.
