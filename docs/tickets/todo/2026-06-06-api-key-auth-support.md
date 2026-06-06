# Add API-key auth support for supported Superset versions

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-api-key-auth-design.md`, `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`, `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `src/superset_agent_cli/config.py`, `README.md`, `docs/architecture/README.md`

## Context

If the repository later targets a Superset version that actually supports Bearer API keys, the CLI could add a cleaner non-interactive auth mode for scripts and automation. That capability should be treated as version-gated rather than assumed available everywhere.

## Definition of done

- [ ] Version support for API-key auth is confirmed for the target Superset release range.
- [ ] The approved API-key auth contract is implemented in config, client, and CLI layers.
- [ ] API-backed commands can authenticate with API keys on supported versions without requiring browser login state.
- [ ] Tests and docs cover version expectations, auth selection, error handling, and usage.

## Notes

Blocked until version support is confirmed and the API-key auth research ticket is resolved.
