# Add embedded-dashboard read commands

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-dashboard-related-resources.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for embedded dashboard configuration, but the CLI currently only reads basic dashboard metadata. Embedded-configuration inspection is a missing read-only dashboard capability that may matter for integrations and environment audits.

## Definition of done

- [x] Client helpers exist for the relevant embedded-dashboard read endpoint or endpoints.
- [x] CLI commands expose embedded-dashboard reads with standard auth and instance guards.
- [x] Tests cover JSON output, human output if applicable, and error handling.
- [x] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket limited to reading embed-related configuration. Do not include embedded write operations.
