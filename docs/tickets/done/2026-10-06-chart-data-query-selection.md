# Evaluate optional query selection for chart-data CSV output

- Status: done
- Priority: low
- Type: research
- Created by: agent
- Created at: 2026-10-06
- Related: [plan](../../plans/2026-10-06-remaining-open-todos.md), [ADR 0012](../../decisions/0012-chart-data-output-contract.md), `tests/test_chart_data.py`

## Context

Optional `--query-index` was proposed to select a table from multi-query CSV. It is not missing functionality from the completed CSV ticket.

## Verified evaluation and decision

The existing multi-query fixture produces independent CSV tables separated by blank rows. Existing JSON preserves `result` as an indexable query list, so consumers needing one query can select it after JSON parsing. CSV quoting/timestamps, multi-table output, and whole-payload failure exits already have runnable tests, which passed during this task.

No concrete recurring selection requirement was established beyond the proposal. Therefore **do not add `--query-index`** or another exit-status contract now. Preserve ADR 0012 and default/raw output. This closes the research task with an explicit no-change outcome, not a claim that an optional feature was implemented.

## Definition of done

- [x] Inspect real implementation and multi-query tests; compare current CSV with existing JSON selection.
- [x] Decide whether selection is warranted: no demonstrated recurring need, no implementation approved.
- [x] Record the outcome and keep current CSV/JSON/exit contracts unchanged.
- [x] Re-run existing success, mixed-query, scalar, failure, quoting, timestamp, and CSV tests.

## Revisit when

A concrete automation repeatedly needs one CSV query and JSON selection is measurably insufficient. Then specify zero-based indexes, format restrictions, invalid-index handling, and selected-versus-whole-payload exit behavior before implementation.
