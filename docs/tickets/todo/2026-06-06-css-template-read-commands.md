# Add CSS-template read commands

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for CSS templates, but the CLI currently has no way to inspect them. CSS templates sit near themes and annotation layers in the broader customization surface, and they are part of the read-only API surface that agents may need to inspect.

## Definition of done

- [ ] A CLI resource group exposes CSS-template list and detail reads.
- [ ] Client helpers wrap the corresponding Superset CSS-template read endpoints.
- [ ] Tests cover human output, JSON output, and guard behavior.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket read-only. Do not include CSS-template creation, updates, or deletion.
