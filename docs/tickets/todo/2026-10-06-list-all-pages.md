# Add opt-in all-page pagination to list commands

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `docs/tickets/done/2026-06-06-superset-client-list-pagination-forwarding.md`, `docs/tickets/todo/2026-10-06-list-filter-parameters.md`, `docs/tickets/todo/2026-10-06-list-column-selection.md`

## Context

An October 6 Pi conversation implemented a temporary pagination loop for an ownership inventory, including count and duplicate checks. List commands currently fetch one page. Raising `--page-size` is not a reliable substitute for fetching every page and can produce incomplete inventories.

## Definition of done

- [ ] Add opt-in `--all` consistently to paginated list commands using a shared client helper.
- [ ] Keep ordinary single-page behavior unchanged; reject ambiguous `--all` plus explicit `--page` combinations and document page-size handling.
- [ ] Preserve filters, selected columns, and ordering across pages; use verified stable ordering where supported.
- [ ] Define the aggregate JSON envelope explicitly and preserve existing single-page contracts.
- [ ] Detect non-progress, premature empty pages, duplicate IDs, and inconsistent counts; fail rather than claim a complete snapshot. Document that pagination cannot provide atomic snapshot isolation.
- [ ] Test multiple pages, empty lists, server page-size limits, changing counts, duplicates, and later-page failures; verify human and JSON output.
- [ ] Write a plan and update README and architecture mappings before declaring implementation complete.

## Notes

Keep this read-only and opt-in. Do not silently retry mutations or add a generic retry framework. Resolve any output-contract change before implementation.
