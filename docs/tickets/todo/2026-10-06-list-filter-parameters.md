# Add structured filter parameters to list commands

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `docs/tickets/done/2026-06-06-list-filtering-and-ordering.md`, `docs/decisions/0011-custom-api-authentication.md`

## Context

Pi conversations on October 2 and 5 used handwritten Superset list queries to filter logs by date and dashboard, and charts by visualization type. Existing list `--search` only supports contains matching on the resource's primary name. The authenticated `api --param` escape hatch already works, but requires manually constructing nested query payloads.

## Definition of done

- [ ] Design a repeatable list `--filter` option supporting column, operator, and typed value; distinguish it clearly from chart-data `--filter col=value`.
- [ ] Verify supported fields/operators against relevant Superset schemas; cover date comparisons and exact visualization-type matches.
- [ ] Extend the existing shared list-query builder and apply the option consistently to list commands.
- [ ] Define composition with `--search`, pagination, and ordering; preserve behavior and JSON envelopes when omitted.
- [ ] Reject malformed values before network access; test human and JSON output, repeated filters, and invalid syntax using mocks.
- [ ] Write an implementation plan, update README examples, and capture any durable syntax decision.

## Notes

No new dependency or live write is needed. Keep raw `api --param` available for uncommon query shapes. Session identifiers and private instance details are deliberately omitted from public documentation.
