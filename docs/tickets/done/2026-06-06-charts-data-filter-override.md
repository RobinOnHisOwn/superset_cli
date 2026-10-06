# charts data filter override

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `docs/tickets/done/2026-06-06-chart-data-fetch.md`, `docs/plans/2026-06-06-chart-data-fetch.md`, `docs/tickets/todo/2026-06-06-explore-read-commands.md`

## Context

`charts data` currently calls `GET /api/v1/chart/{pk}/data/`, which runs the chart with its saved `query_context` exactly as stored. There is no way to ask for "this saved chart, but restricted to April 2026" or "this saved chart filtered to a specific dimension value". In practice this means agents must either find a chart already pre-filtered to the slice they want, or give up.

Many charts on real dashboards rely on dashboard-level filters at render time. When fetched via the saved-chart endpoint with no override they either return a much broader window than expected, or return empty/null payloads.

Superset exposes `POST /api/v1/chart/data` for caller-supplied `query_context`. The minimal useful step is to keep the saved chart's `query_context` as the base, apply a small set of override knobs supplied on the CLI, and POST the result.

This is distinct from the planned `explore` commands, which expose explore *state* metadata and do not trigger a filtered query.

## Definition of done

- [ ] Client helper that fetches a saved chart's `query_context`, applies override knobs, and POSTs to `/api/v1/chart/data`.
- [ ] CLI options on `charts data` for at least: time range override (e.g. `--time-range`), and one or more `--filter col=value` style adhoc filters appended to the existing `query_context`.
- [ ] Behavior with no overrides is identical to today (still uses the GET endpoint, or POSTs the unchanged saved `query_context`).
- [ ] JSON output remains the raw Superset payload. Human output unchanged.
- [ ] Tests cover: no-override parity with today's behavior, time-range override path, single-filter override path, unknown-chart and auth-state error paths reuse existing patterns.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Completion evidence

Implemented repeatable string equality filters and time-range overrides on copied saved query contexts, with CSRF-enabled POST execution and unchanged no-override GET behavior. `tests/test_chart_data_overrides.py` covers JSON/dict contexts, preserved filters, invalid inputs, and missing/invalid contexts. Existing chart-data tests retain auth/not-found guards. Full suite: 579 passed; CLI help and build passed. README and architecture updated; see ADR 0015. No live verification performed.

## Notes

Stays within read-only posture: the override still triggers a SQL read against the backing database, which is what every Superset chart render already does. No chart state is mutated server-side.

A short design note in `docs/plans/` is warranted before implementation to decide the exact override surface (only `--time-range` first? full `--filter` shape?) and how to merge overrides into a saved `query_context` safely.
