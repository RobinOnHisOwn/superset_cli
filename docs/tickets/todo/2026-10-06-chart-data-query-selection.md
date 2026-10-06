# Evaluate optional query selection for chart-data CSV output

- Status: todo
- Priority: low
- Type: research
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/cli.py`, `tests/test_chart_data.py`, `docs/decisions/0012-chart-data-output-contract.md`, `docs/tickets/done/2026-06-06-charts-data-csv-output.md`

## Context

The conversation analysis proposed `charts data --csv --query-index N` to avoid extracting one table from a multi-query payload. Fresh origin/main already implements CSV output, but concatenates tables with blank-line separators. ADR 0012 deliberately rejected requiring a query index. Optional selection is a new proposal, not an unfinished part of that completed ticket.

## Definition of done

- [ ] Verify a concrete multi-query use case where current CSV output creates recurring parsing work; compare with using existing JSON output.
- [ ] Decide whether optional `--query-index` is warranted; do not reopen completed CSV work solely because the parameter was proposed.
- [ ] If approved, write a plan and update ADR 0012 to distinguish optional selection from mandatory selection.
- [ ] Specify zero-based indexing, invalid/out-of-range behavior, and whether the option is CSV-only. Preserve default CSV behavior and raw JSON output.
- [ ] Define whether exit status evaluates the selected query or the entire payload, including failed or empty selected queries alongside successful siblings.
- [ ] If implemented, add failing tests first for selection, invalid indexes, quoting/timestamps, exit behavior, and no-option parity; update help and README.
- [ ] Record the verified outcome, including a no-change decision if the current output is sufficient.

## Notes

Chart time-range/filter overrides and CSV output are already implemented in origin/main and have completed tickets. Do not create duplicate todos for those capabilities.
