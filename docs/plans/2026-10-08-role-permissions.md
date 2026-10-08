# Guarded role permission management

**Date:** 2026-10-08

## Goal

Fill the missing permission discovery, role inspection, and exact replacement capabilities without rebuilding user/role CRUD or claiming complete service-account provisioning.

## Research and prerequisites

- **Verified:** existing role CRUD changes names only; it does not expose FAB role permissions. Existing paginated traversal, CSRF transport, bounded OpenAPI reference resolver, and write guard are reusable.
- **Verified:** FAB 5.2.2 [permission metadata API](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/permission_view_menu/api.py) lists `id`, nested `permission.name`, and `view_menu.name` under `/api/v1/security/permissions-resources/`.
- **Verified:** [role API](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/role/api.py) GET `/roles/{role_id}/permissions/` returns flat permission objects. POST `/roles/{role_id}/permissions` replaces the entire collection despite its add-oriented name and silently drops unknown IDs. [Schema](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/role/schema.py) requires integer `permission_view_menu_ids`.
- **Proposed and approved:** focused CLI commands, expected role name and explicit expected/current and desired permission pairs, fail-closed metadata/contract validation, and exact read-back.
- **Unknown:** target enablement, backend/custom builtin-role semantics, group/synchronized effective user roles, cross-user key integration, and isolated live acceptance. Do not claim these are verified by direct role grants.
- Consulted ADRs 0009, 0020, 0023, and 0024. No dependency/default/existing JSON changes, no live mutations, no automatic retries, and no commit/push authorization.

## Planned changes

1. Add `tests/test_role_permissions.py` using native-shaped transport fixtures. Confirm new read commands and replacement tests fail because capabilities are absent. Cover human/JSON output, forced/no-color help, guard-before-access, invalid IDs/specs, missing/ambiguous metadata, incomplete pagination, identity/grant drift, explicit empty expected bootstrap, unchanged no-op, exact single POST, failed/mismatched read-back, uncertain errors, and no redirect replay.
2. Extend `client.py` and `cli.py` only: `security permissions` lists metadata with existing list controls; `security roles permissions` inspects direct grants; `security roles permissions-set` consumes existing `--body`/`--file` JSON with exactly `expected_role_name`, `expected_permissions`, and `permissions`. Each pair is a two-string JSON array. Empty arrays are explicit intent, never defaulted. Resolve IDs from complete metadata, require target OpenAPI integer-list POST contract before writes, compare exact role identity/current pairs, and verify IDs plus names after POST. Report requested/effective grants, write status, verification and warning; ambiguous writes/read-back failures exit nonzero. Never automatically revert/retry a sent permission mutation.
3. Update README, architecture, decision index and an ADR. Move the permission capability ticket into in-progress and update its links; close only the scoped direct-grant capability work, leaving service-user effective-role and live gates explicitly open.

## Verification

- Red then green: `direnv exec "$PWD" uv run pytest tests/test_role_permissions.py -v`.
- Existing security/list/write/owner tests, then full `uv run pytest -v` under locked CI uv and Python 3.12/3.13 when available.
- CLI top-level/new command help, guarded nonexistent-instance smoke, `uv build`, doc-link tests, spec validation, and `git diff --check`.
- No remote CI or live-instance acceptance claim.

## Results

- New-capability red run: 21 failed, 16 passed (missing commands); schema-negative red run: three failed, 40 passed.
- Focused existing/new checks: 483 passed. Final role tests: 43 passed.
- CI-pinned uv 0.12.23, locked dependencies: full Python 3.12 and 3.13 suites each 1,115 passed, 13 skipped.
- Top-level/write-command help, guarded missing-instance smoke (exit 1 before access), build, isolated wheel help, repo/doc checks and whitespace checks passed.
- No live operations or remote CI. Existing spec validator error: architecture README filename does not match its inferred plan pattern.
- Permission capability ticket remains in-progress because complete effective-user identity/permission evidence is still separate and unverified. Source changes are uncommitted.

## Decision follow-up

Decision record update required: `docs/decisions/0026-guarded-role-permissions.md` for exact replacement semantics, explicit expected state, and the direct-grant/effective-user distinction.
