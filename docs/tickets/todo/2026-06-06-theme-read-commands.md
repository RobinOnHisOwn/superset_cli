# Add theme read commands

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for themes, but the CLI currently cannot inspect them. Theme reads are a smaller gap than core analytics resources, but they are still part of the available read-only API surface.

## Definition of done

- [ ] A CLI resource group exposes theme list and detail reads.
- [ ] Client helpers wrap the corresponding Superset theme read endpoints.
- [ ] Tests cover human output, JSON output, and guard behavior.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket limited to reading themes. Do not include theme activation or modification.
