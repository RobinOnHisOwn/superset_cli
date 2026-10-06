# Replace a chart's owner list safely

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `docs/tickets/done/2026-10-06-chart-owner-discovery.md`, `docs/tickets/done/2026-10-06-dashboard-owner-replacement.md`, `docs/decisions/0009-write-command-explicit-opt-in.md`, `docs/decisions/0010-write-scope-expansion.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_writes.py`

## Context

Generic `charts update --body` already forwards arbitrary update payloads. A focused owner operation should validate IDs and report effective ownership without introducing another transport. Superset 6.0 accepts `{"owners": [...]}` via `PUT /api/v1/chart/{pk}`, checks ownership, and computes the replacement using the shared owner helper. Non-admin callers omitted from the requested list are retained by the server.

## Definition of done

- [x] Complete supported-version verification from chart owner discovery; write an implementation plan and failing tests. Approve proposed command names/options and JSON shape.
- [x] Accept positive integer user IDs, reject malformed inputs, and deduplicate; do not resolve ambiguous display names automatically.
- [x] Reuse `get_chart` and `update_chart`. Resolve UUID input through chart details to a numeric ID before PUT; the verified write contract takes an integer primary key.
- [x] Send only the owners field. Do not modify params, query context, dataset linkage, dashboard membership, or dashboard/dataset ownership; do not invoke the existing query-context-clearing option for this operation.
- [x] Use `_require_allow_write` before writes. Missing `--allow-write` exits non-zero naming the intended owner replacement and missing flag; help includes "Required to actually perform the write. Without it the command is a dry-run."
- [x] Require explicit clear intent for an empty owner list, distinct from omitted input. Document possible non-admin retention and ownership/permission requirements.
- [x] Read back effective owners and report IDs/names in human and JSON output. Explain discrepancies rather than claiming exact replacement; distinguish successful mutation with failed read-back from a write that never occurred, without blind retries.
- [x] Test replacement, duplicates, invalid/unknown IDs, omitted/empty input, retained caller, UUID resolution, missing opt-in with zero writes, 403/404/422, unrelated-field preservation, and read-back failure.
- [x] Update README and architecture mappings; run targeted tests, full pytest, CLI help smoke checks, and build. No live write without explicit authorization.

## Completion evidence

Implemented `charts owners-set`, repeated positive `--owner-id`, explicit `--clear`, UUID-to-numeric resolution, target integer-owner PUT schema validation, literal opt-in, owner-only existing update/CSRF transport, and authoritative effective-owner read-back. Retention/mismatch and failed read-back exit 1 with evidence; network write uncertainty is distinct from a no-op, with no retries. **187 owner tests and 843 full-suite tests passed**, build/help/guard smoke checks passed. Plan: `docs/plans/2026-10-06-owner-management.md`; durable contract: ADR 0020. No live mutation; generic update/query-context behavior unchanged.

## Notes

**Verified:** Chart updates are within ADR 0010 and require ADR 0009's guard. The 6.0 PUT response echoes submitted properties, so it is not authoritative evidence of effective owners. Owner-only updates use the ownership-checked path, not the report-worker query-context exception.

**Proposed:** A focused owner replacement operation alongside the generic update command. Reuse dashboard-owner validation/reporting patterns if they exist; avoid a speculative resource framework.

**Unknown:** Target-version capabilities and permissions. New upstream editor/viewer subject IDs are not interchangeable with user owner IDs; unsupported deployments need a clear error.

Sources:
- https://github.com/apache/superset/blob/6.0.0/superset/charts/api.py
- https://github.com/apache/superset/blob/6.0.0/superset/charts/schemas.py
- https://github.com/apache/superset/blob/6.0.0/superset/commands/chart/update.py
- https://github.com/apache/superset/blob/6.0.0/superset/commands/utils.py

No durable decision change is made by this ticket. Record lasting CLI contract or compatibility choices when implementation is planned.
