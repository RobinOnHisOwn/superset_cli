# Add current-user and instance-metadata read commands

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

The CLI can validate auth by reading `/api/v1/me/`, but it does not expose richer read-only metadata such as current-user roles, menu structure, or available domains. These endpoints are useful for agents that need lightweight environment introspection before acting on other resources.

## Definition of done

- [ ] Client helpers exist for the approved user and instance-metadata read endpoints.
- [ ] CLI commands expose a small, coherent set of metadata reads in human and JSON modes.
- [ ] Tests cover output behavior and standard guard paths.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep the surface focused on lightweight environment introspection rather than broad security administration.
