# Add only missing security role permission-management capabilities

- Status: in-progress
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-08
- Related: [service role](../todo/2026-10-07-minimal-cache-service-role.md), [backend research](2026-10-07-service-key-provisioning-integration.md), [write guard ADR](../../decisions/0009-write-command-explicit-opt-in.md), `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

User/role CRUD already exists. Determine whether existing commands can discover permission/resource pairs and inspect/assign exact role grants; implement only the missing pieces needed for the four-permission service role. Do not rebuild CRUD or add a speculative service-account abstraction.

## Definition of done

- [x] Inspect existing code, nearby tests, version-pinned backend schemas, and relevant decision records; record which discovery/read/assignment capabilities are present versus missing.
- [x] If existing commands fully cover the need, document their verified usage and add no new commands. Otherwise write a short plan and failing tests for only the gaps.
- [x] Resolve actual permission IDs by exact permission/resource pairs using supported metadata; reject missing or ambiguous matches.
- [ ] Inspect target identity and current/effective permissions before writes; reject unexpected privilege drift or incomplete evidence. Support explicit expected initial state for new roles without silently adopting existing roles.
- [x] Reuse the shared transport and literal per-invocation `--allow-write` guard for every remote mutation; missing opt-in sends no requests.
- [x] Read back assignments and compare exact sets, not subsets. Do not add Admin or extra permissions to make validation pass.
- [x] Test human/JSON output where applicable, guard behavior, ambiguity, drift, failed read-back, and uncertain transport outcomes. Preserve existing output contracts; never automatically retry sent mutations.
- [x] Run focused tests, full pytest, CLI smoke checks, and build for code changes; update README and any changed structural mappings. Live tests require explicit isolated-instance authorization.

## Implemented direct-grant capabilities

[Plan](../../plans/2026-10-08-role-permissions.md) and [ADR 0026](../../decisions/0026-guarded-role-permissions.md) record the missing native interfaces: role CRUD changes names only; permission/resource discovery, direct-grant inspection, and guarded exact replacement are now implemented and locally tested. FAB's add-oriented POST replaces all grants. Explicit expected ID/name/current pairs, including verified empty bootstrap state, reject observed role drift. Verification covers stored direct role grants only, not complete effective user permissions; the effective-identity checkbox remains open and is coordinated with the service-role ticket. No cross-user key implementation or live mutation is included.

## Verification evidence

- Initial new capability checks: 21 failed, 16 passed; absent CLI commands caused the expected failures. Additional schema-negative checks: three failed before object/required-field validation was strengthened.
- Focused role/security/owner/write/list checks: 483 passed. Final role tests: 43 passed.
- Locked CI uv 0.12.23: Python 3.13.12 and Python 3.12 each 1,115 passed, 13 skipped.
- Build, top-level/new write help, isolated built-wheel command help, repo/documentation checks (47 with role tests), missing-opt-in/no-config smoke (exit 1), and whitespace checks passed.
- Spec validation still reports the existing architecture README filename-classification error. Ubuntu/remote CI and live effective-role/key acceptance were not run.

## Notes

Depends on verified backend permission-management schemas, not on inventing cross-user key REST support. 1Password and caller dataset allowlists are out of scope.
