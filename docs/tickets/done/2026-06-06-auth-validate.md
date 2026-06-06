# Auth validate command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_auth_validate.py`, `docs/architecture/README.md`

## Context

`auth validate <instance>` is already implemented. It uses the stored browser session to call `/api/v1/me/` and confirms live authentication against Superset.

## Definition of done

- [x] The command requires a known instance and saved storage state.
- [x] `--json` returns authenticated user data in a stable shape.
- [x] Auth-expired and network errors are surfaced through CLI error handling and the client is closed after use.

## Notes

The command relies on `SupersetClient.get_current_user()`.
