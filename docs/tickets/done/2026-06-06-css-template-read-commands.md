# Add CSS-template read commands

- Status: done
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for CSS templates, but the CLI currently has no way to inspect them. CSS templates sit near themes and annotation layers in the broader customization surface, and they are part of the read-only API surface that agents may need to inspect.

## Definition of done

- [x] A CLI resource group exposes CSS-template list and detail reads.
- [x] Client helpers wrap the corresponding Superset CSS-template read endpoints.
- [x] Tests cover human output, JSON output, and guard behavior.
- [x] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket read-only. Do not include CSS-template creation, updates, or deletion.
