# Design the security/admin read surface

- Status: todo
- Priority: medium
- Type: research
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `docs/decisions/0001-read-only-bootstrap-scope.md`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes many read endpoints for security and administration, including roles, users, groups, permissions, resources, and row-level security. The CLI currently exposes none of them. Because this surface is broad and potentially sensitive, the repository should first decide which subset belongs in an agent-friendly CLI.

## Definition of done

- [ ] The highest-value security/admin read endpoints are identified and scoped.
- [ ] Risks around sensitive output, permissions, and usability are documented.
- [ ] A recommended initial command surface is captured in a short plan.
- [ ] Follow-up implementation tickets exist for the approved subset.

## Notes

Keep this work read-only. The goal is to narrow the surface before adding commands.
