# Add query history read commands

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read-only query-history endpoints that can help agents inspect recent SQL Lab activity, but the CLI currently has no `queries` command group. Adding query-history reads would extend the tool's operational usefulness without leaving the read-only product posture.

## Definition of done

- [x] A new CLI resource group exposes query-history list and detail reads.
- [x] Client helpers wrap the corresponding Superset query endpoints.
- [x] Tests cover human output, JSON output, and guard behavior.
- [x] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket limited to reading query history. Do not include stop, execute, or other write-like SQL Lab actions.
