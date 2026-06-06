# Add direct JWT auth support

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-jwt-auth-design.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `src/superset_cli/config.py`, `README.md`, `docs/architecture/README.md`

## Context

The CLI currently depends on browser session cookies for API access. Superset also documents direct JWT login and refresh flows, which could help in simpler deployments that support credential-based API auth.

## Definition of done

- [ ] The approved JWT auth contract is implemented in config, client, and CLI layers.
- [ ] The CLI can authenticate and refresh access using the documented Superset JWT endpoints for supported setups.
- [ ] Tests cover happy paths, refresh behavior, and failure handling.
- [ ] `README.md` and `docs/architecture/README.md` document JWT auth setup and limitations.

## Notes

Implement this only after the JWT auth contract is designed.
