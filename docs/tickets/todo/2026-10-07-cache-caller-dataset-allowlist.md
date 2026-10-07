# Reject unapproved cache dataset targets before authentication

- Status: todo
- Blocker review (2026-10-07): this repository contains the reusable CLI, not the identified automation caller. No caller repository, policy owner or approved instance-to-dataset mapping was supplied. Preserve existing CLI defaults; implement in the owning caller after those facts are verified. See [review plan](../../plans/2026-10-07-open-key-todos.md).
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: [cache implementation and live acceptance](../in-progress/2026-10-07-targeted-cache-invalidation.md), [ADR 0024](../../decisions/0024-targeted-cache-controls.md), [service role](2026-10-07-minimal-cache-service-role.md), `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

Prevent an automated caller from accidentally invalidating unapproved dataset IDs. This is a local caller safeguard, not server-side dataset isolation: a holder of the key can bypass the caller and directly request invalidation.

## Verified knowledge

- Existing `cache invalidate` requires positive numeric IDs and `--allow-write`; the client deduplicates IDs and maps them to `<ID>__table` UIDs.
- Current flow is write guard → instance lookup → `_require_storage_state` → `_client` → invalidation. SupersetClient construction reads the bound key or saved auth file, so a guard inside the POST transport would be too late.
- Client invalidation performs an OpenAPI request before the POST. Rejection must precede this and any auth preflight, browser-cookie import, or secret lookup by an orchestration wrapper.
- FAB key scopes are not enforced by its key-validation path. CacheRestApi's permission is not a per-dataset authorization boundary.

## Proposed placement and open contract

Prefer the owning automation caller's existing configuration and entry point; no general CLI default/configuration change is approved by this ticket. Inspect that caller repository before implementation. If a reusable CLI policy is needed, approve its configuration/precedence and ensure enforcement across all covered entry points rather than only one wrapper.

## Definition of done

- [ ] Identify the actual caller and configuration owner; write its implementation plan. Record whether only cache invalidation is covered and which alternate call paths are outside the safeguard.
- [ ] Require an explicit local allowlist. Fail closed for missing, empty, malformed, or unreadable policy; never fetch policy from Superset to decide whether network access is allowed.
- [ ] Validate requested and allowed IDs as positive integers (reject booleans and malformed values), deduplicate, and reject the entire invocation when any requested ID is outside the allowlist. Do not send an allowed subset silently.
- [ ] Perform the check before credential/environment-key lookup, saved-state reads, subprocess secret retrieval, browser imports, client construction, or any network request.
- [ ] Bind policy to the explicitly selected instance so IDs from one instance cannot accidentally authorize another. Approve this mapping rather than invent deployment names.
- [ ] Keep the literal per-invocation `--allow-write` requirement; the allowlist is not write authorization.
- [ ] Write failing tests that install credential/network/subprocess sentinels and prove zero access for mixed allowed/denied targets, missing/invalid policy, wrong instance, and malformed IDs; verify the approved path still uses existing cache transport.
- [ ] Document bypass limitations prominently: operators requiring security isolation need backend enforcement, not this check or stored API-key scopes.
- [ ] Run the owning caller's focused/broader tests; if CLI behavior is approved and changed, also verify CLI human/JSON output and update its README.

## Sources

- [Superset cache API](https://github.com/apache/superset/blob/6.1.0/superset/cachekeys/api.py)
- [FAB manager](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/manager.py)
- Repository entry points: `cache_invalidate`, `_require_storage_state`, `_client`, `SupersetClient.__init__`, `invalidate_dataset_cache`.

## Decision follow-up

Decision record update required in the owning caller repository: fail-closed policy source, instance binding, covered entry points, and non-isolation guarantee. Review ADR 0024 if a CLI policy is proposed.
