# Decide whether to expand beyond read-only scope

- Status: todo
- Priority: high
- Type: decision
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/decisions/0001-read-only-bootstrap-scope.md`, `README.md`, `src/superset_agent_cli/cli.py`

## Context

The current product scope is explicitly read-only, but Superset exposes many write-capable API features that are still absent from the CLI. Before implementing any of them, the repository needs an explicit scope decision about whether write operations are allowed, for which resource types, and under what safety constraints.

## Definition of done

- [ ] The allowed and disallowed write-capable feature areas are decided explicitly.
- [ ] Safety expectations for write operations are documented.
- [ ] `docs/decisions/0001-read-only-bootstrap-scope.md` is updated or superseded if scope changes.
- [ ] Follow-up implementation tickets are linked to the approved scope.

## Notes

This ticket is the gate for all server-side write operations.
