# Add tag read commands

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for tags and tagged objects, but the CLI currently has no tag-related command group. Read-only tag inspection would help agents discover asset organization without changing server state.

## Definition of done

- [ ] A CLI resource group exposes tag list and detail reads, and any small high-value related read that fits the existing command pattern.
- [ ] Client helpers wrap the corresponding Superset tag read endpoints.
- [ ] Tests cover human output, JSON output, and guard behavior.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket read-only. Do not include tag creation, tagging, favorites, or deletion.
