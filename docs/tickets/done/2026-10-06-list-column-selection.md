# Add selected-column parameters to list commands

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: [plan](../../plans/2026-10-06-remaining-open-todos.md), [ADR 0022](../../decisions/0022-explicit-list-query-controls.md), `tests/test_list_controls.py`

## Context

Projected reads reduce response size without fetching every field and trimming locally.

## Definition of done

- [x] Repeat `--columns FIELD` once per unique field across all 15 resource/security lists.
- [x] Verify against resource list metadata and forward through `q.columns`; no guessed universal catalog.
- [x] Preserve defaults and raw single-page envelopes; human projection emits compact JSON rows instead of missing-field placeholders.
- [x] Reject empty, duplicate, or malformed selections before access; report unsupported fields clearly.
- [x] `--all` uses server `ids` or existing record IDs without silently adding ID to the requested projection.
- [x] Test composed query controls, forwarding, invalid input, projected human output, and unchanged JSON envelopes.
- [x] Update plan, README, architecture, and policy record.

## Completion evidence

The tests exercise a projection without record IDs across multiple pages, verifying exactly the requested `q.columns` and aggregate identity metadata. Server-side column pruning was verified in FAB source, motivating the explicit metadata check. Focused red/green and full verification are recorded in the linked plan. No dependency or live instance access was added.
