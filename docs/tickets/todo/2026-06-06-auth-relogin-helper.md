# Add auth re-login helper flow

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-auth-session-expiry-reporting.md`, `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`, `src/superset_agent_cli/auth.py`, `src/superset_agent_cli/cli.py`, `README.md`, `docs/architecture/README.md`

## Context

The current auth flow can report missing or expired local session state, but it does not offer a streamlined re-login or refresh helper. Since session expiry is a normal operational case in the current browser-based model, the CLI should make recovery easier.

## Definition of done

- [ ] A clear re-login or refresh-oriented CLI flow exists for expired or missing session state.
- [ ] The chosen flow integrates cleanly with the existing browser-login model and error messages.
- [ ] Tests cover common expired-session recovery paths.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

This ticket is about UX and recovery flow, not adding a new auth backend.
