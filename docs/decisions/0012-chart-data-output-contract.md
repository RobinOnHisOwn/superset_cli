# 0012: Chart-data output and exit contract

- Status: accepted
- Date: 2026-10-06
- Related: `docs/plans/2026-10-06-autonomous-todos.md`, `src/superset_cli/cli.py`, `tests/test_chart_data.py`

## Context

Scripts need a failure exit when chart queries fail or yield no rows, while retaining the raw response for diagnosis. Tabular consumers also need CSV without reparsing the JSON envelope.

## Decision

`charts data` emits its selected output before checking payload-level failure. It exits 1 if all queries have an explicit non-success status, reporting the first available error, or if no successful query has rows. Missing status is accepted for legacy payloads. Mixed results succeed if at least one successful query has rows. Zero and NULL scalar values are legitimate rows; we do not infer measure semantics.

`--csv` uses the standard library CSV writer and `colnames` ordering, one table per query separated by a blank line. Numeric `__timestamp` values convert from epoch milliseconds to ISO-8601 UTC; other columns and nonnumeric or out-of-range timestamps remain unchanged. `--csv` and `--json` are mutually exclusive. JSON shape remains unchanged, including on failure.

## Consequences

Existing scripts must check exit codes; callers can still inspect raw JSON after failure. CSV is deliberately a sequence of tables rather than a merged schema. List/get commands are unaffected.

## Alternatives considered

### Treat NULL measures as empty

Rejected: the payload does not identify a universally valid measure column, and NULL may be legitimate. Only failed queries and absence of rows are detected.

### Require a query index for CSV

Rejected: blank-line-separated tables cover multiple queries without another selection option or silently dropping data.
