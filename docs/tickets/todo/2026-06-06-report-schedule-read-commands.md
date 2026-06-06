# Add report-schedule read commands

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes read endpoints for report schedules and schedule logs, but the CLI currently has no scheduled-report inspection commands. Read-only access would help agents understand alerting and reporting configuration without leaving the repository's safe posture.

## Definition of done

- [ ] A CLI resource group exposes report-schedule list and detail reads, and optionally report log reads if they fit the same command pattern.
- [ ] Client helpers wrap the corresponding Superset report read endpoints.
- [ ] Tests cover human output, JSON output, and guard behavior.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Do not include report creation, updates, or deletion in this ticket.
