# Add selected-column parameters to list commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `docs/tickets/todo/2026-10-06-list-filter-parameters.md`, `docs/tickets/todo/2026-10-06-list-all-pages.md`

## Context

October 2 and 5 Pi conversations manually added `columns` to API queries to retrieve only dashboard IDs or selected chart metadata. Dedicated list commands cannot request selected columns, resulting in unnecessarily large responses and extra parsing for agents.

## Definition of done

- [ ] Add `--columns` to list commands using the shared query builder; choose and document a simple repeatable or comma-separated syntax.
- [ ] Forward selection through the API's existing `q.columns` mechanism after verifying resource support; do not merely fetch everything and trim locally.
- [ ] Preserve default output and response envelopes when omitted; handle projected records in human-readable output without misleading missing-field placeholders.
- [ ] Reject empty/malformed selection and report unsupported fields clearly.
- [ ] Define interaction with `--all`, including internal identity fields needed for duplicate checks without silently changing the requested projection.
- [ ] Test query forwarding, composed query controls, human and JSON output, and invalid input.
- [ ] Write an implementation plan and update README examples; record any lasting output decision.

## Notes

Selected fields are resource-specific. Do not hardcode a guessed universal field catalog or add JSONPath/jq-like expression parsing.
