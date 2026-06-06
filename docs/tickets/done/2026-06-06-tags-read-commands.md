# Add tag read commands

- Status: done
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for tags and tagged objects, but the CLI currently has no tag-related command group. Read-only tag inspection would help agents discover asset organization without changing server state.

## Definition of done

- [x] A CLI resource group exposes tag list and detail reads, and any small high-value related read that fits the existing command pattern.
- [x] Client helpers wrap the corresponding Superset tag read endpoints.
- [x] Tests cover human output, JSON output, and guard behavior.
- [x] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket read-only. Do not include tag creation, tagging, favorites, or deletion.
