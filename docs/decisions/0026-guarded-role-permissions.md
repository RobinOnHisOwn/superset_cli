# 0026: Guarded exact replacement of direct role permissions

- Status: accepted
- Date: 2026-10-08
- Related: [plan](../plans/2026-10-08-role-permissions.md), [write guard](0009-write-command-explicit-opt-in.md), [owner verification](0020-guarded-resource-owners.md), `src/superset_cli/client.py`, `src/superset_cli/cli.py`, `tests/test_role_permissions.py`

## Context

Generic role CRUD changes names, not grants. FAB 5.2.2 exposes permission/resource metadata and direct role permissions separately. Its `add_role_permissions` POST replaces the entire collection and silently omits IDs that no longer exist. An echoed request is not proof of stored grants. Least-privilege setup needs exact metadata and explicit expected state, not guessed IDs or an assumed meaning for role names.

## Decision

Expose permission discovery and direct role-grant inspection using existing list/read transport. Provide guarded exact replacement with a JSON body containing exactly `expected_role_name`, `expected_permissions`, and `permissions`. Pair arrays contain permission/resource names; explicit empty arrays mean empty expected state or intentional clearing. Require literal per-invocation `--allow-write` before credentials/network access, including no-ops.

Resolve positive IDs from complete target metadata; reject malformed or duplicate IDs/pairs, missing pairs, incompatible target integer-list POST schema, mismatched role ID/name, and unexpected current grants. Never silently adopt an existing role or broaden it with Admin. Send only `permission_view_menu_ids` to the exact source-verified POST path; do not follow mutation redirects or retry sent requests.

Verify role identity and the exact set of stored IDs/names after acknowledged POST. Structured output distinguishes no-op, acknowledged write, uncertain write, failed verification and mismatched grants. Sent mutation errors are conservatively uncertain; read-back failure after acknowledged success retains `write_performed=true`. All uncertain/unverified results exit nonzero with inspection guidance. Do not automatically restore a before-image that could overwrite concurrent edits.

Verification is explicitly limited to stored direct role grants. Builtin/custom roles, group-derived or synchronized effective user permissions, active service-user identity, privileged cross-user key management and live acceptance remain separate requirements. These commands do not provision a service account or prove its effective least privilege.

## Consequences

Expected-state checks catch observed drift but are non-atomic; no deployment precondition/ETag mechanism is assumed. Complete metadata traversal can fail under concurrent changes and intentionally blocks writes. Operators need enabled compatible FAB security APIs and discovery/role permissions; this implementation changes no server configuration. Native current-user keys remain governed by ADRs 0023/0025. No live mutations were performed.

## Alternatives considered

- Generic raw API commands only: already possible, but leave exact ID resolution, expected-state checks and read-back entirely to each caller.
- Incremental add/remove wrappers: misleading because the native POST replaces all grants, and read-modify-write still races. Use explicit whole-set intent instead.
- Automatic service-account provisioning or rollback: requires independent effective-role, ownership and recovery contracts; do not infer them from direct role metadata or overwrite concurrent work.

## Evidence

FAB 5.2.2: [role endpoints](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/role/api.py), [role schemas](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/role/schema.py), [permission/resource metadata](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/permission_view_menu/api.py). Transport-backed tests exercise native response shapes without real credentials or a live server.
