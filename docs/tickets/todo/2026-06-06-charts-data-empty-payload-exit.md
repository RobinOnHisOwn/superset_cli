# charts data exit code on empty or errored payloads

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `docs/tickets/done/2026-06-06-cli-api-error-mapping.md`, `docs/tickets/done/2026-06-06-chart-data-fetch.md`

## Context

`charts data` currently exits 0 even when the Superset response contains no usable result:

- All queries returned zero rows.
- A query returned `status != "success"` (Superset includes the failure inside the payload, not as an HTTP error).
- Every row's measure column is `NULL` (e.g. upstream ETL hasn't loaded yet).

This makes scripted use unreliable: the CLI silently produces "success" output and downstream tooling has to re-parse the payload to find out it got nothing. The existing `_api_errors()` mapping handles HTTP-level failures well, but payload-level emptiness is invisible to it.

## Definition of done

- [ ] When all queries in the response have `status` other than `"success"`, exit non-zero with a concise stderr message including the first error message.
- [ ] When every query returns zero rows, exit non-zero with a clear stderr message (e.g. `chart returned 0 rows`).
- [ ] Behavior is gated so it does not regress charts whose legitimate output is a single-row scalar (e.g. `big_number` charts where `rowcount == 1` and a value is present must remain exit 0).
- [ ] JSON output is still emitted to stdout on the failure paths so callers can inspect the raw payload; only the exit code and a short stderr line change.
- [ ] Tests cover: success path unchanged, all-error path, all-empty path, mixed (one query succeeds, one is empty), and the single-row scalar path stays exit 0.
- [ ] `README.md` notes the new exit-code contract for `charts data`.

## Notes

Treat this as a contract change for `charts data` only. Do not extend the same heuristic to other list/get commands without a separate ticket, since their "empty" semantics differ.
