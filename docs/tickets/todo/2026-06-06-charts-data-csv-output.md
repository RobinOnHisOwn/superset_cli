# charts data CSV output and timestamp conversion

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `docs/tickets/done/2026-06-06-chart-data-fetch.md`

## Context

`charts data` today returns either a short human summary or the raw Superset JSON payload. For analysis workflows the JSON form is awkward:

- Each row is wrapped in a `result[].data` envelope; agents and humans both end up writing throwaway parsing code to extract rows.
- Time-axis columns (typically named `__timestamp`) are epoch milliseconds. Every downstream consumer needs to convert them.
- Multi-query payloads (Superset returns one entry per query in `result`) need to be flattened or kept separate explicitly.

A tabular output mode would cut both token use for LLM consumers and friction for shell pipelines.

## Definition of done

- [ ] New `--csv` (and/or `--format csv`) option on `charts data` that emits one CSV per query in `result`, with column headers from `colnames`.
- [ ] Epoch-millisecond timestamp values (heuristic: column name `__timestamp` or `coltypes` flag indicating temporal) are emitted as ISO-8601 UTC strings in CSV mode. JSON mode behavior unchanged.
- [ ] For multi-query payloads, choose and document one of: concatenated with a blank-line separator, or `--query-index N` to pick one. Pick the simpler option and explain why in the plan.
- [ ] Tests cover: single-query CSV output, multi-query CSV output, epoch-ms conversion, and that JSON mode is unaffected.
- [ ] `README.md` updated with an example.

## Notes

Keep the conversion narrow. Only `__timestamp`-style columns should auto-convert; other numeric columns must round-trip unchanged.
