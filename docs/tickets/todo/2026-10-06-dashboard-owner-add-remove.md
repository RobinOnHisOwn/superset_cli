# Add and remove dashboard owners without dropping co-owners

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `docs/tickets/todo/2026-10-06-dashboard-owner-discovery.md`, `docs/tickets/todo/2026-10-06-dashboard-owner-replacement.md`, `docs/decisions/0009-write-command-explicit-opt-in.md`, `docs/decisions/0010-write-scope-expansion.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_writes.py`

## Context

Operators need to add a co-owner or remove an obsolete owner without manually constructing the entire list. Superset 6.0's dashboard update accepts a replacement list, not an atomic add/remove operation. Build these conveniences on the verified inspection/replacement work rather than introducing another HTTP path.

## Definition of done

- [ ] Complete owner discovery and replacement first; write an implementation plan and failing tests before code. Approve proposed command names/options and JSON output contract.
- [ ] Read current owners, compute a deduplicated union for add or subtraction for remove, and submit only the resulting owner list using existing transport.
- [ ] Preserve unrelated owners and dashboard fields. Reuse replacement validation, slug resolution, safety checks, and effective-owner read-back rather than duplicating them.
- [ ] Require literal `--allow-write` on every invocation, including already-present/already-absent no-ops. Missing opt-in exits non-zero with the intended mutation; include ADR 0009's required help wording.
- [ ] With opt-in, already-present adds and already-absent removals report a no-op without a PUT.
- [ ] Removing the last owner requires the explicit clear intent defined by replacement. Explain that non-admin self-removal can be rejected in effect because Superset retains the caller; never claim a transfer or removal that read-back disproves.
- [ ] Test multiple existing owners, duplicate input, no-ops, last-owner removal, retained caller, unknown user IDs, missing opt-in, API failures, and effective-state discrepancies in both human and JSON modes.
- [ ] Document read-modify-write concurrency limits: a replacement can overwrite a concurrent ownership change. Do not claim atomicity or invent ETag support; verify any server-side precondition support before relying on it.
- [ ] Update README and architecture mappings; run focused tests, full pytest, CLI help smoke checks, and build. No live mutation without explicit authorization.

## Notes

**Verified:** Superset 6.0 computes replacement owners from `owners` and preserves existing owners only when that field is omitted. Non-admin callers cannot remove themselves through omission from the list.

**Proposed:** Single-dashboard ID-based add/remove convenience operations. Bulk reassignment, user deletion workflows, recursive chart/dataset ownership changes, username resolution, and editor/viewer migration are out of scope.

**Unknown:** Target-version concurrency/precondition support; this must not be presented as an atomic owner-membership API.

Source: https://github.com/apache/superset/blob/6.0.0/superset/commands/utils.py
