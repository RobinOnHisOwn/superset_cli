# 0015: Saved chart query overrides without persistence

- Status: accepted
- Date: 2026-10-06
- Related: `docs/plans/2026-10-06-autonomous-todos.md`, `tests/test_chart_data_overrides.py`, `src/superset_cli/client.py`

## Context

Dashboard filters are not applied when reading the saved chart's data endpoint. Callers need a narrowly filtered result without changing saved chart definitions.

## Decision

No-override reads retain `GET /api/v1/chart/{pk}/data/`. With overrides, fetch chart metadata, parse and deep-copy its saved `query_context`, replace each query's `time_range` when supplied, and append equality filters to each query. `--filter col=value` is repeatable and treats values as strings. Do not merge schemas, infer metric types, or edit saved chart state. Invalid or absent contexts fail before query execution.

Execute the copied context through `/api/v1/chart/data` with existing CSRF handling. This dedicated chart-data operation is a read of chart results, not a chart update. It does not expand SQL Lab or arbitrary API permissions; custom non-GET API commands still require `--allow-write` under ADR 0011.

## Consequences

Existing filters and datasource/query definitions are preserved. Callers must save a usable context in Explore first. Overrides may execute database queries like an ordinary chart read, but never persist chart changes. No live instance was queried for implementation verification.

## Alternatives considered

### Edit the saved chart before fetching data

Rejected: it would mutate shared dashboard behavior for a transient read.

### Build a query context from chart params when missing

Rejected: it would duplicate frontend query-construction logic and guess plugin-specific semantics.
