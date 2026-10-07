# Add targeted dataset cache invalidation

- Status: in-progress
- Implemented 2026-10-07: guarded numeric/deduplicated targets, source-verified UID mapping, runtime OpenAPI schema gate, shared cookie/JWT/API-key/CSRF transport, truthful acceptance JSON/human output, and no write replay. ADR 0024; focused tests: 90 passed; full suite passes; built wheel verified.
- Blocked: isolated live eviction acceptance needs explicit live-mutation authorization and a target with verified tracking/backend alignment. No such target/authorization was supplied. HTTP success must not be substituted for this gate. All CLI implementation work is complete.
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: `2026-10-07-chart-data-force-refresh.md`, `2026-10-07-chart-data-cache-diagnostics.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_client.py`, `tests/test_writes.py`, `tests/test_api_key_auth.py`, `docs/decisions/0009-write-command-explicit-opt-in.md`, `docs/decisions/0010-write-scope-expansion.md`, `docs/decisions/0023-environment-bound-api-keys.md`

## Context

Expose Superset's native `POST /api/v1/cachekey/invalidate` through a focused CLI command. Dataset-wide invalidation should cover tracked filtered query entries, unlike warming an unfiltered chart or refreshing just one query. The generic `api` command already provides transport; reuse client/authentication/write-guard patterns.

## Proposed CLI scope

`superset-cli cache invalidate INSTANCE --dataset ID [--dataset ID ...] --allow-write [--json]`

Targeting is mandatory. No all-datasets default, dashboard-wide implicit targeting, Redis flush, or direct backend deletion.

## Prerequisites and compatibility findings

- Verify the target's OpenAPI schema and permissions. Superset 6.1 accepts `datasource_uids`; verify mapping from a dataset ID to the API's datasource UID rather than confusing it with a dataset UUID.
- Dataset-based invalidation requires server-side `STORE_CACHE_KEYS_IN_METADATA_DB=True`. Existing untracked entries are not retroactively indexed. Document these external prerequisites; this ticket does not enable server flags or implement their migration.
- Pinned Superset 6.1 code deletes tracked keys through `cache_manager.cache`, while chart results use `cache_manager.data_cache`. Different backend/database/prefix configurations can therefore return success without removing chart results. Chart 0.22.4 defaults `DATA_CACHE_CONFIG = CACHE_CONFIG`, so mismatch is not universal. Verify the target configuration; do not claim every 6.1 deployment is safe.
- The endpoint may log incomplete deletion, remove metadata records, and still return 201. A successful response or retry does not prove eviction. An empty success response cannot justify invented deleted-key counts.
- Reuse configured cookie/JWT/API-key authentication and CSRF handling. Machine callers need an independently provisioned credential; the CLI must not create service users/keys, change SAML, or fall back to human browser credentials in API-key mode.

## Definition of done

- [ ] Write an implementation plan and failing tests first. Confirm supported endpoint/schema, dataset UID conversion, and permissions; approve command/output contracts.
- [ ] Require at least one valid explicit target; validate and deduplicate repeat dataset IDs. Determine whether numeric IDs only or verified UUID resolution is supported, and document it.
- [ ] Use the shared `_require_allow_write` guard before network/auth access. Without literal `--allow-write`, exit non-zero naming the intended invalidation and missing flag. Include ADR 0009's required dry-run help wording.
- [ ] Reuse existing client factory, request handling, CSRF, and auth modes. Send only targeted datasource UIDs; do not mutate datasets, chart configuration, sessions, or Celery state.
- [ ] Support human and JSON output. Report requested targets and server outcome accurately; describe HTTP success as request acceptance rather than proven eviction unless separately verified. Preserve existing output contracts elsewhere.
- [ ] Test missing opt-in/targets, malformed and repeated IDs, exact URL/body, credential/CSRF behavior, empty 201 responses, 400/401/403/500, timeout, and unsupported endpoint. Never silently retry a sent write during auth recovery; surface ambiguous outcomes and allow explicit operator reruns.
- [ ] With explicit authorization in an isolated test instance, pre-cache multiple native-filter combinations plus an unrelated dataset. Invalidate only the targets; verify normal non-forced rendered dashboard requests cannot reuse old results, unrelated cached results remain, and session/Celery state is preserved. HTTP success alone is insufficient. Missing tracking or incompatible backends block that verification, not trigger a Redis fallback.
- [ ] Update README/help with examples, external tracking/backend prerequisites, untracked-entry limitations, and safe failure/rerun guidance. Update architecture mappings for the new command group.
- [ ] Run focused tests, full pytest, CLI help/manual smoke checks, and build. Record actual evidence and unverified compatibility.

## Scope boundary

Only the reusable CLI command, tests, and documentation belong here. Superset flag rollout, service-account/secret provisioning, existing-entry transition execution, Dagster post-dbt sensors, and warming schedules belong to their owning deployment/orchestration repositories. Never flush shared Redis or delete session/Celery data.

## Research references

- https://raw.githubusercontent.com/apache/superset/6.1.0/superset/cachekeys/api.py
- https://raw.githubusercontent.com/apache/superset/6.1.0/superset/cachekeys/schemas.py
- https://raw.githubusercontent.com/apache/superset/6.1.0/superset/common/query_context_processor.py
- https://raw.githubusercontent.com/apache/superset/6.1.0/superset/utils/cache.py
- https://superset.apache.org/developer-docs/6.1.0/api/invalidate-cache-records-and-remove-the-database-records/

## Decision follow-up

Decision record update required at implementation: targeted invalidation scope, truthful success/output semantics, and compatibility constraints in `docs/decisions/`; review ADR 0010's approved write surface and preserve ADR 0009's guard. This TODO makes no deployment change.
