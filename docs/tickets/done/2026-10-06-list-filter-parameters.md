# Add structured filter parameters to list commands

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: [plan](../../plans/2026-10-06-remaining-open-todos.md), [ADR 0022](../../decisions/0022-explicit-list-query-controls.md), `tests/test_list_controls.py`

## Context

Typed list filtering should not require handwritten API envelopes or a replacement transport.

## Definition of done

- [x] Repeatable JSON-object `--filter` preserves typed values and is distinct from chart-data `col=value` syntax.
- [x] Verify fields/operators through resource `_info`, or native list validation when that route returns 404; malformed metadata and 403 never fall back.
- [x] Apply the shared query builder to all 15 paginated lists, including security resources.
- [x] Filters AND together and append to search; preserve pagination, ordering, and ordinary JSON envelopes.
- [x] Reject malformed/non-finite values before network/browser access; test repeated filters and human/JSON output.
- [x] Document syntax, examples, version evidence, and the lasting policy.

## Completion evidence

FAB 5.2.2 source verifies datetime `gt`/`lt` and equality operators; Superset 6.1.0 chart `viz_type` and log `dttm` search fields were inspected. The log API omits `_info`; regression tests verify its guarded 404 fallback and no fallback on 403. No universal field catalog or new dependency was added. Focused red/green tests and full verification are recorded in the linked plan. No live requests were used.
