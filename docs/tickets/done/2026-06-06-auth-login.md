# Auth login command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/auth.py`, `src/superset_agent_cli/config.py`, `tests/test_auth.py`, `docs/architecture/README.md`

## Context

`auth login <instance>` is already implemented. It requires a known instance, derives auth-state paths, launches the browser login flow, and reports the saved paths.

## Definition of done

- [x] Unknown instances are rejected before browser work starts.
- [x] The command derives a profile directory and storage-state path for the instance.
- [x] `--json` returns the instance name, base URL, profile directory, and storage-state path.

## Notes

The interactive browser implementation lives in `login_with_browser`.
