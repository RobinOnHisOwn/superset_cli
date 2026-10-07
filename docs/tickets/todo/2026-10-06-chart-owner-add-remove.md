# Add and remove chart owners without dropping co-owners

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `docs/tickets/todo/2026-10-06-chart-owner-discovery.md`, `docs/tickets/todo/2026-10-06-chart-owner-replacement.md`, `docs/tickets/todo/2026-10-06-dashboard-owner-add-remove.md`, `docs/decisions/0009-write-command-explicit-opt-in.md`, `docs/decisions/0010-write-scope-expansion.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_writes.py`

## Context

Adding or removing one chart owner should preserve other owners without requiring an operator to assemble a complete replacement payload. Superset 6.0's chart update takes a replacement list, not atomic membership operations. Build these conveniences on chart owner inspection/replacement, reusing existing validation and transport.

## Definition of done

- [ ] Complete chart owner discovery/replacement; write an implementation plan and failing tests, and approve proposed command names/options and JSON output.
- [ ] Read current owners and compute a deduplicated union for add or subtraction for remove; submit only the owners field and preserve unrelated chart settings and ownership on other resources.
- [ ] Reuse replacement validation, UUID-to-ID resolution, opt-in checks, and effective-owner read-back. Reuse matching dashboard-owner patterns when available without adding speculative abstractions.
- [ ] Require literal `--allow-write` for every invocation, including no-ops; missing opt-in exits non-zero naming the intended mutation. Include ADR 0009's required help wording.
- [ ] With opt-in, adding an existing owner or removing an absent owner reports a no-op without a PUT.
- [ ] Require explicit clear intent when removing the last owner. Explain non-admin caller retention and never claim self-removal or transfer that effective-owner read-back disproves.
- [ ] Cover multiple co-owners, duplicates, no-ops, unknown IDs, last-owner removal, retained caller, UUID lookup, missing opt-in, API errors, and read-back discrepancies in human and JSON tests.
- [ ] Document read-modify-write concurrency limits: replacement can overwrite a concurrent owner change. Do not claim atomicity or assume ETag/precondition support without verification.
- [ ] Update README and architecture mappings; run targeted tests, full pytest, CLI help smoke checks, and build. No live mutation without explicit authorization.

## Notes

**Verified:** Superset 6.0 chart updates use `compute_owners`; shared owner logic preserves existing owners when omitted and retains non-admin callers when missing from an explicit replacement.

**Proposed:** Single-chart ID-based add/remove operations. Bulk reassignment, user deletion, changes to all charts in a dashboard, username resolution, and editor/viewer migration are out of scope.

**Unknown:** Target-version concurrency/precondition support and permissions; inspect before implementation.

Sources:
- https://github.com/apache/superset/blob/6.0.0/superset/commands/chart/update.py
- https://github.com/apache/superset/blob/6.0.0/superset/commands/utils.py
