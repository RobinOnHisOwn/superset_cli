# Add annotation-layer read commands

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for annotation layers and their annotations, but the CLI currently has no way to inspect them. This is a missing read-only analytics feature area that may matter for chart interpretation.

## Definition of done

- [ ] A CLI resource group exposes annotation-layer list and detail reads, plus any closely related read needed for practical inspection.
- [ ] Client helpers wrap the corresponding Superset annotation-layer read endpoints.
- [ ] Tests cover human output, JSON output, and guard behavior.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Prefer the smallest useful surface before adding nested annotation operations.
