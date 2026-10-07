# Add opt-in all-page pagination to list commands

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: [plan](../../plans/2026-10-06-remaining-open-todos.md), [ADR 0022](../../decisions/0022-explicit-list-query-controls.md), `tests/test_list_controls.py`

## Definition of done

- [x] Shared `_list_resource` implements opt-in `--all` for all 15 paginated resource/security lists.
- [x] Preserve ordinary single-page behavior; reject explicit `--page` with `--all`; use positive requested page size (default 100), respecting server caps.
- [x] Preserve filters/projection/order across pages. Use ID ordering only when advertised; otherwise retain explicit/server ordering.
- [x] Aggregate JSON is exactly `{count, ids, result}`; single-page raw envelopes stay unchanged.
- [x] Fail on duplicate/non-progressing identities, premature empty pages, mismatched/invalid counts or identity metadata, and later-page failures. Do not emit partial aggregate output.
- [x] Test multiple pages, zero rows, capped page sizes, count changes, duplicates, missing IDs, failure paths, and human/JSON output.
- [x] Document memory buffering, non-atomic snapshot limitations, plan, README, and architecture mapping.

## Completion evidence

Mocked transport verifies every resource's page zero/one traversal with server caps, projected records lacking IDs, unchanged query controls, and strict failure exits. Superset 6.1.0 charts do not advertise ID ordering; tests prevent inventing support. Equal counts and distinct IDs cannot prove atomic snapshot isolation, and the docs explicitly say so. Red/green and full verification are recorded in the linked plan. No live requests or retry framework were added.
