# Add chart data fetch command

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

The CLI can inspect chart metadata but cannot fetch the underlying payload for a saved chart. Superset exposes a read-only chart data endpoint, and supporting it would make the CLI more useful for agent analysis and validation tasks.

## Definition of done

- [ ] The exact saved-chart data endpoint and required request shape are confirmed against current Superset docs or behavior.
- [ ] A client helper and CLI command expose read-only chart data retrieval for an existing chart.
- [ ] Tests cover the request contract, output modes, and error handling.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

This ticket may need a short design note first if the endpoint requires non-trivial request payload choices or multiple output modes.
