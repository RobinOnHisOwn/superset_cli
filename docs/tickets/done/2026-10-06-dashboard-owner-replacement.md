# Replace a dashboard's owner list safely

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `docs/tickets/done/2026-10-06-dashboard-owner-discovery.md`, `docs/decisions/0009-write-command-explicit-opt-in.md`, `docs/decisions/0010-write-scope-expansion.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_writes.py`

## Context

Generic `dashboards update --body` already supports forwarding an owner payload; no new transport or dependency is needed. A focused operation should validate owner IDs, explain replacement semantics, and report the effective owners. Superset 6.0 accepts an integer owner list via `PUT /api/v1/dashboard/{pk}`. Its update command checks ownership, validates users, and replaces the owner list; non-admin callers omitted from the requested list are added back by the server.

## Definition of done

- [x] Depend on owner discovery's supported-version verification; write an implementation plan and failing tests first. Treat dedicated command spelling/options and JSON shape as proposed until approved.
- [x] Accept explicit positive user IDs, reject malformed inputs, and deduplicate IDs. Do not infer users from display names.
- [x] Reuse `get_dashboard` and `update_dashboard`; resolve slugs to numeric dashboard IDs for writes because the verified upstream PUT contract takes an integer primary key.
- [x] Send only `{"owners": [...]}`; preserve all other dashboard properties and do not alter chart/dataset ownership or viewing roles.
- [x] Route through `_require_allow_write` before any write. Without `--allow-write`, exit non-zero naming the intended replacement and missing flag; help includes the mandatory dry-run wording from ADR 0009.
- [x] Require explicit clear intent for an empty list, separate from omitted owner input. Document that non-admin callers may be retained and clearing does not necessarily produce an ownerless dashboard.
- [x] Read back the dashboard after mutation and report effective owner IDs/names in human and JSON output. If actual owners differ from requested owners, explain the discrepancy rather than claiming exact replacement. Distinguish a successful PUT followed by failed verification from an unperformed write; do not blindly retry.
- [x] Cover replacement, duplicates, empty/omitted input, invalid/unknown IDs, retained caller, slug resolution, missing opt-in with zero writes, 403/404/422, and post-write verification failure in tests.
- [x] Update README and architecture mappings; run targeted tests, full pytest, CLI help smoke checks, and build. No live mutation without explicit user authorization.

## Completion evidence

Implemented `dashboards owners-set`, repeated positive `--owner-id`, explicit `--clear`, slug-to-numeric resolution, target integer-owner PUT schema validation, literal opt-in, owner-only existing update/CSRF transport, and authoritative effective-owner read-back. Retention/mismatch and failed read-back exit 1 with evidence; network write uncertainty is distinct from a no-op, with no retries. **187 owner tests and 843 full-suite tests passed**, build/help/guard smoke checks passed. Plan: `docs/plans/2026-10-06-owner-management.md`; durable contract: ADR 0020. No live mutation; generic update behavior unchanged.

## Notes

**Verified:** This fits the dashboard-update scope in ADR 0010 and must obey ADR 0009. Existing generic dashboard update need not be replaced. Superset 6.0's PUT response contains submitted properties, not a definitive effective-owner snapshot; read-back is necessary.

**Proposed:** A focused owner replacement command using IDs, not a new generic security administration surface.

**Unknown:** Target version's empty-list behavior and permissions. New upstream `editors`/`viewers` use a different subject model; unsupported deployments must receive a clear error, not an improvised compatibility conversion.

Sources:
- https://github.com/apache/superset/blob/6.0.0/superset/dashboards/schemas.py
- https://github.com/apache/superset/blob/6.0.0/superset/dashboards/api.py
- https://github.com/apache/superset/blob/6.0.0/superset/commands/dashboard/update.py
- https://github.com/apache/superset/blob/6.0.0/superset/commands/utils.py (`compute_owner_list`, `populate_owner_list`)

No durable decision change is made by this ticket. Record any lasting CLI contract or compatibility choice when implementation is planned.
