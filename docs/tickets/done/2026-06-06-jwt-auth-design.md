# Design direct JWT auth support

- Status: done
- Priority: medium
- Type: research
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `src/superset_cli/config.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset documents direct JWT login and refresh endpoints, but not all self-hosted deployments will expose a practical credential-based flow for this CLI. Before implementation, the repository should decide when direct JWT auth is worth supporting and how it should coexist with browser sessions and with any future version-gated API-key support.

## Definition of done

- [x] The supported JWT login scenarios and non-goals are documented.
- [x] The expected credential inputs, provider assumptions, token refresh behavior, and secret-handling approach are documented.
- [x] Interaction with session-cookie auth and any future version-gated API-key support is documented.
- [x] A recommended implementation plan is captured and linked to follow-up code work.

## Notes

Prefer a narrow, explicit contract over assuming all Superset authentication backends behave the same way.
