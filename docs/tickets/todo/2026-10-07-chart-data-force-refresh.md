# Force fresh chart results from the CLI

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: `2026-10-07-chart-data-cache-diagnostics.md`, `2026-10-07-targeted-cache-invalidation.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_chart_data.py`, `tests/test_chart_data_overrides.py`, `docs/decisions/0012-chart-data-output-contract.md`

## Context

`charts data` can return cached results but has no force-refresh option. Existing time-range and filter overrides already use the saved query context; extend that flow rather than introducing another transport. Refreshing one query is not dataset-wide invalidation.

## Definition of done

- [ ] Write a short implementation plan and failing tests first. Verify supported Superset versions' force-refresh request contract for both saved-chart reads and query-context POSTs; do not guess parameter placement.
- [ ] Add `charts data INSTANCE CHART_ID --force`, reusing `SupersetClient.get_chart_data` and existing authentication/CSRF handling. Force the exact requested query, including every query in multi-query contexts, without changing saved chart configuration.
- [ ] Preserve existing filters, time ranges, datasource, and default no-option behavior; support force refresh alongside `--time-range`, repeated `--filter`, `--json`, and `--csv`.
- [ ] Clarify whether the verified endpoint refreshes/replaces cache entries or merely bypasses them. Apply existing write-safety policy where applicable; record any durable decision about read-like POSTs and refresh effects rather than silently changing that policy.
- [ ] Test request serialization, saved contexts in object/string form, unchanged no-option requests, multi-query behavior, unsupported/missing contexts, auth/permission failures, and API errors.
- [ ] Preserve raw JSON shape, CSV output, and ADR 0012 exit semantics. Update help and README with the difference between force refresh and invalidation.
- [ ] Run focused tests, full pytest, CLI help smoke checks, and build. An authorized live check must establish fresh results, not merely HTTP success; no live writes without authorization.

## Scope boundary

CLI behavior only. No Superset deployment changes, Dagster sensors, Redis operations, cache warming, or global flush.

## Decision follow-up

Record lasting request/safety choices in `docs/decisions/` when implementation is planned; no runtime decision is enacted by this ticket.
