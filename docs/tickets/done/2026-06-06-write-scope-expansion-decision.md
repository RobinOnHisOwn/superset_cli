# Decide whether to expand beyond read-only scope

- Status: done
- Priority: high
- Type: decision
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/decisions/0001-read-only-bootstrap-scope.md`, `README.md`, `src/superset_cli/cli.py`

## Context

The current product scope is explicitly read-only, but Superset exposes many write-capable API features that are still absent from the CLI. Before implementing any of them, the repository needs an explicit scope decision about whether write operations are allowed, for which resource types, and under what safety constraints.

## Definition of done

- [x] The allowed and disallowed write-capable feature areas are decided explicitly.
- [x] Safety expectations for write operations are documented.
- [x] `docs/decisions/0001-read-only-bootstrap-scope.md` is updated or superseded if scope changes.
- [x] Follow-up implementation tickets are linked to the approved scope.

## Notes

This ticket is the gate for all server-side write operations.

## Resolution

Closed 2026-06-06. Scope expansion is captured in `docs/decisions/0010-write-scope-expansion.md`, which supersedes ADR 0001. The safety contract from ADR 0009 (`--allow-write` per invocation) is reused unchanged. Linked implementation tickets were unblocked and closed in the same rollout (`docs/plans/2026-06-06-write-command-rollout.md`).
