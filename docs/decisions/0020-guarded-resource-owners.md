# 0020: Guarded chart and dashboard owners

- Status: accepted
- Date: 2026-10-06
- Related: [implementation plan](../plans/2026-10-06-owner-management.md), [ADR 0009](0009-write-command-explicit-opt-in.md), [ADR 0010](0010-write-scope-expansion.md), `src/superset_cli/client.py`, `src/superset_cli/cli.py`, `tests/test_owners.py`

## Context

Superset 6.0 charts and dashboards expose independent owner collections. Updates replace an integer user-ID list, not atomic membership operations. The PUT response echoes submitted properties and does not prove effective ownership: shared `compute_owner_list`/`populate_owner_list` retain non-admin callers. Newer upstream editor/viewer subject models are not equivalent. Generic update transport already exists, but it cannot validate a dedicated ownership workflow's intended/effective state on its own.

## Decision

Provide matching focused owner inspection, eligible-owner discovery, replacement, add, and remove commands for both resources. Preserve existing detail/update JSON. Use server-returned positive user IDs and existing getters/CSRF-protected updates; resolve chart UUIDs/dashboard slugs through details to a numeric primary key. Inspectors distinguish absent/malformed ownership from empty ownership; numeric-ID responses must match the requested resource.

Require the shared literal per-invocation `--allow-write` guard before any API request, including no-ops. Replacements send only `owners`; explicit `--clear` distinguishes intentional emptiness from omitted input and authorizes last-owner removal. Deduplicate IDs without accepting booleans or resolving display names. An already-effective owner list performs no PUT.

Check the target OpenAPI integer-owner PUT schema before every mutation. Candidate discovery verifies the related-field query schema and preserves the filtered response envelope. Resolve only bounded local schema references/inheritance; missing, conflicting, cyclic, foreign, or incompatible contracts fail closed. Do not silently convert owner IDs to editor/viewer subject IDs or fall back to a broader user directory.

After successful PUT, read the numeric resource back. Mutation output contains requested IDs, effective owner objects, write_performed, verified, matches_requested, and warning. Mismatches and unverifiable read-back emit evidence and exit 1, never silently claim an exact transfer/self-removal. A network error during the mutation reports an unknown outcome (`write_performed: null`), not a definite no-op; a successfully acknowledged write followed by read failure reports `write_performed: true`. Neither case automatically retries the mutation.

## Consequences

Owner commands fit the existing chart/dashboard update scope and retain the visible guardrail. Runtime capability checks cost an OpenAPI GET per candidate discovery or opted-in mutation and may block otherwise usable deployments with incomplete schemas; operators must verify compatibility rather than bypass validation. Add/remove still uses non-atomic read-modify-write and can overwrite concurrent changes. No ETag/precondition support is assumed. Live deployment acceptance and permissions remain operator checks; implementation/testing performs no live mutation.

## Alternatives considered

### Generic update payloads only

Still available, but require operators to implement positive-ID checks, explicit clear semantics, slug/UUID resolution, and effective-owner verification independently.

### Fixed-version assumptions or editor/viewer conversion

Rejected: deployment versions and forks differ; user IDs and subject IDs have different semantics. Capability checks and explicit incompatibility are safer than guessed conversion.

### Trust PUT output or automatically retry verification failures

Rejected: echoed requested IDs can hide retained callers; replaying an acknowledged or uncertain mutation can overwrite later edits. Distinguish outcomes and require inspection before retries.

## Evidence

Pinned Superset 6.0 sources: [dashboard schemas](https://github.com/apache/superset/blob/6.0.0/superset/dashboards/schemas.py), [chart schemas](https://github.com/apache/superset/blob/6.0.0/superset/charts/schemas.py), [related query](https://github.com/apache/superset/blob/6.0.0/superset/views/base_api.py), [related owner filters](https://github.com/apache/superset/blob/6.0.0/superset/views/filters.py), [owner computation](https://github.com/apache/superset/blob/6.0.0/superset/commands/utils.py). Transport-backed tests cover both resources without real credentials or live access.
