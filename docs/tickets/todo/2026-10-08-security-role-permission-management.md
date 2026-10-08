# Add only missing security role permission-management capabilities

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-08
- Related: [service role](2026-10-07-minimal-cache-service-role.md), [backend research](2026-10-07-service-key-provisioning-integration.md), [write guard ADR](../../decisions/0009-write-command-explicit-opt-in.md), `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

User/role CRUD already exists. Determine whether existing commands can discover permission/resource pairs and inspect/assign exact role grants; implement only the missing pieces needed for the four-permission service role. Do not rebuild CRUD or add a speculative service-account abstraction.

## Definition of done

- [ ] Inspect existing code, nearby tests, version-pinned backend schemas, and relevant decision records; record which discovery/read/assignment capabilities are present versus missing.
- [ ] If existing commands fully cover the need, document their verified usage and add no new commands. Otherwise write a short plan and failing tests for only the gaps.
- [ ] Resolve actual permission IDs by exact permission/resource pairs using supported metadata; reject missing or ambiguous matches.
- [ ] Inspect target identity and current/effective permissions before writes; reject unexpected privilege drift or incomplete evidence. Support explicit expected initial state for new roles without silently adopting existing roles.
- [ ] Reuse the shared transport and literal per-invocation `--allow-write` guard for every remote mutation; missing opt-in sends no requests.
- [ ] Read back assignments and compare exact sets, not subsets. Do not add Admin or extra permissions to make validation pass.
- [ ] Test human/JSON output where applicable, guard behavior, ambiguity, drift, failed read-back, and uncertain transport outcomes. Preserve existing output contracts; never automatically retry sent mutations.
- [ ] Run focused tests, full pytest, CLI smoke checks, and build for code changes; update README and any changed structural mappings. Live tests require explicit isolated-instance authorization.

## Notes

Depends on verified backend permission-management schemas, not on inventing cross-user key REST support. 1Password and caller dataset allowlists are out of scope.
