# Add permalink resolution read commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for resolving dashboard, Explore, and SQL Lab permalink keys, but the CLI currently has no way to inspect those saved states. These endpoints are useful when an agent receives a shared permalink and needs to understand the referenced state without using the browser UI.

## Definition of done

- [ ] The supported permalink read endpoints are identified and exposed through a coherent CLI command surface.
- [ ] Client helpers wrap the corresponding Superset permalink read endpoints.
- [ ] Tests cover JSON output, human output if applicable, and standard guard paths.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket focused on resolving existing permalinks, not creating new ones.
