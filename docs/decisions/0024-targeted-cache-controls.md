# 0024: Targeted cache controls with truthful acceptance reporting

- Status: accepted
- Date: 2026-10-07
- Related: [implementation plan](../plans/2026-10-07-complete-open-todos.md), [write guard](0009-write-command-explicit-opt-in.md), [chart output](0012-chart-data-output-contract.md), `tests/test_cache_controls.py`

## Context

Operators need fresh chart queries, per-query cache evidence, and targeted dataset invalidation without direct backend access. Superset 6.1.0 implements these surfaces, but invalidation success does not prove chart-result eviction. CacheRestApi deletes through `cache_manager.cache`, whereas chart results use `data_cache`; tracked metadata can be removed even if backend deletion is incomplete.

## Decision

Expose the existing server mechanisms only. `charts data --force` uses GET `force=true` for saved-chart reads or top-level boolean `force` in copied override query contexts. It affects every query in that context, not every native-filter combination. Superset bypasses cache reads and normally writes successful results back under their query keys; disabled caching remains disabled. Require literal `--allow-write` before auth/network access for this deliberate cache refresh. Existing non-force reads and ADR 0015 overrides remain unchanged.

Opt-in `--cache-info` adds per-query human diagnostics from the existing response: `is_cached`, `cache_key`, `cached_dttm`, and `cache_timeout`. Missing fields are unknown; null, false, zero, and -1 remain distinct. Only -1 denotes disabled caching in the verified contract; zero is reported without inventing its deployment-specific meaning. JSON/CSV output and ADR 0012 exit rules remain unchanged.

`cache invalidate INSTANCE --dataset ID [--dataset ID ...] --allow-write` accepts positive numeric dataset IDs, deduplicates them, and maps SQLA datasets to source-verified `<ID>__table` UIDs, not UUIDs. Validate the target's OpenAPI POST request schema for string `datasource_uids`, then reuse configured cookie/JWT/API-key auth and CSRF transport. Server RBAC remains authoritative (`CacheRestApi` invalidate permission); the CLI does not grant permissions or provision credentials. No retry of a sent invalidation.

The JSON envelope is `{dataset_ids, datasource_uids, accepted, eviction_verified, response}`. A successful request sets `accepted=true`, `eviction_verified=false`, and preserves the server response, including an empty object for empty 201. Never invent counts or claim eviction. Network failures report unknown outcomes and require inspection before an explicit rerun.

## Consequences

Requires external `STORE_CACHE_KEYS_IN_METADATA_DB=True`, tracked entries, and compatible cache/data-cache backend, database, and key-prefix configurations. Previously untracked entries are not retroactively indexed. The CLI cannot infer these conditions from OpenAPI or HTTP success. Live acceptance remains unverified: an explicitly authorized isolated instance must demonstrate multiple normal non-forced filter combinations refresh while unrelated dataset entries and session/Celery state remain intact. No Redis flush/fallback, configuration rollout, service-account provisioning, or orchestration is included.

New cache capabilities use unpublished version 0.3.0 because PyPI 0.2.0 was verified as already published. No package is published by this change.

## Alternatives considered

- Generic `api` only: retains transport but makes target validation, UID conversion, and truthful acceptance reporting each caller's responsibility.
- Unguarded force refresh: resembles a read but intentionally changes cached state; explicit invocation permission makes that effect visible.
- Automatically inspect/delete Redis: bypasses server permissions, risks unrelated data, and still cannot establish rendering freshness. Rejected.
- Optional CSV query selection: no recurring concrete use case supplied; preserve existing blank-line-separated CSV and raw JSON rather than add another output/exit contract.

## Sources

Pinned Superset 6.1.0: [chart-data API](https://github.com/apache/superset/blob/6.1.0/superset/charts/data/api.py), [schemas](https://github.com/apache/superset/blob/6.1.0/superset/charts/schemas.py), [query cache manager](https://github.com/apache/superset/blob/6.1.0/superset/common/utils/query_cache_manager.py), [SQLA UID](https://github.com/apache/superset/blob/6.1.0/superset/connectors/sqla/models.py), [invalidation API](https://github.com/apache/superset/blob/6.1.0/superset/cachekeys/api.py), [invalidation schema](https://github.com/apache/superset/blob/6.1.0/superset/cachekeys/schemas.py), [tracking](https://github.com/apache/superset/blob/6.1.0/superset/utils/cache.py).
