# Chart data fetch

## Goal

Add a read-only `charts data` command that returns the underlying data payload of a saved chart.

## API choice

Superset exposes two routes for chart data:

- `POST /api/v1/chart/data` — caller supplies a full `query_context` body. Powerful but requires constructing query state outside Superset.
- `GET /api/v1/chart/{pk}/data/` — server uses the saved chart's stored `query_context`. No client-side state required.

The GET form is the right fit for read-only inspection of an existing saved chart: it does not need a request body, does not let the caller modify chart state, and matches the existing `charts get` and `dashboards charts` ergonomics.

Note: this triggers a SQL query against the backing database. That stays within the repository's read-only API posture (the database read is what every Superset chart already does on render); we do not introduce write semantics.

## CLI shape

- `charts data <instance> <pk> [--json]`
- `--json` returns the raw Superset payload (queries list with data rows).
- Human output prints a short summary: number of queries, total row count, and the first column header per query if available.

## Client helper

- `SupersetClient.get_chart_data(pk: str) -> dict` calling `/api/v1/chart/{pk}/data/` and returning the raw payload (no `result` unwrap; the response is shaped as `{"result": [<query>, ...]}` so unwrap to the list would lose top-level metadata if any future fields appear).

## Tests

- `tests/test_chart_data.py`:
  - JSON output returns raw payload
  - human output shows summary
  - not-found path
  - unknown instance, missing auth state, network error use existing patterns and are covered elsewhere

## Decision follow-up

No durable decision change. Confirms current read-only scope is broad enough to include server-computed data reads of saved charts.
