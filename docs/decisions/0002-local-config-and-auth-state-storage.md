# 0002: Local config and auth state storage

- Status: accepted
- Date: 2026-06-05
- Related: `src/superset_agent_cli/config.py`, `src/superset_agent_cli/auth.py`, `tests/test_config.py`, `tests/test_instances_add.py`, `tests/test_auth_status.py`

## Context

The CLI needs persistent local knowledge of configured Superset instances and saved browser authentication state. This data must be easy for local commands to find, simple to inspect during testing, and separate from the application source tree.

## Decision

Store configuration and saved auth state in standard per-user local paths:

- config: `~/.config/superset-agent-cli/config.yaml`
- auth/browser state directory: `~/.local/share/superset-agent-cli/`

Within the state directory, keep per-instance subdirectories for browser profile data and `storage-state.json`.

## Consequences

- Local state is stable across CLI invocations and outside the repository working tree.
- Tests can override these paths with temporary directories without changing implementation structure.
- Future agents must treat these files as sensitive local artifacts and never commit them.

## Alternatives considered

### Store everything inside the repository

Rejected because repository-local state is easy to commit by mistake and couples machine-specific artifacts to source control.

### Require environment variables for every path

Rejected because the default user experience would become noisy and fragile. Optional overrides are enough for tests and special cases.
