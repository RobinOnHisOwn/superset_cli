# Expose chart-result cache diagnostics

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: `2026-10-07-chart-data-force-refresh.md`, `2026-10-07-targeted-cache-invalidation.md`, `src/superset_cli/cli.py`, `tests/test_chart_data.py`, `docs/decisions/0012-chart-data-output-contract.md`

## Context

`charts data --json` already preserves the complete server response, but human output shows only row and column summaries. Operators need to distinguish cached results from fresh execution and correlate individual filtered queries with their cache entries.

## Definition of done

- [ ] Verify supported Superset response fields and semantics before implementation; write a plan and failing tests. Determine whether default human output or an explicit diagnostic option is appropriate and approve any output-contract change.
- [ ] Report per-query cache hit/miss, key, cached timestamp, and timeout when supplied by the server. Distinguish missing/unknown values from false, zero, disabled caching, and a genuine cache miss; do not invent fields or infer freshness from HTTP success.
- [ ] Reuse the existing chart-data response without extra requests, Redis access, or a custom cache abstraction. Keep queries distinguishable in multi-query responses.
- [ ] Preserve raw `--json` shape, machine-readable CSV output, and ADR 0012 failure/empty-result exit semantics. Cache diagnostics must not expose credentials or hidden request headers.
- [ ] Test cached/fresh responses, absent/null metadata, zero/disabled timeouts, multiple queries, and errored/empty results in human and JSON output; ensure CSV stays unchanged.
- [ ] Update help/README with examples showing how diagnostics complement force refresh and dataset invalidation. Explain that native-filter combinations may have different keys.
- [ ] Run focused tests, full pytest, CLI help smoke checks, and build.

## Scope boundary

CLI presentation only. No Superset configuration, Dagster integration, cache administration, direct Redis inspection, or promise of backend-wide cache inventory.

## Decision follow-up

Record any lasting human-output contract in `docs/decisions/` when implementation is planned; preserve ADR 0012's existing JSON/CSV contract.
