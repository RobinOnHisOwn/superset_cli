# 0002: Local config and auth state storage

- Status: accepted
- Date: 2026-06-05
- Related: `docs/plans/2026-06-06-superset-cli-rename.md`, `src/superset_cli/config.py`, `src/superset_cli/auth.py`, `tests/test_config.py`, `tests/test_instances_add.py`, `tests/test_auth_status.py`

## Context

The CLI needs persistent local knowledge of configured Superset instances and saved browser authentication state. This data must be easy for local commands to find, simple to inspect during testing, and separate from the application source tree.

## Decision

Store configuration and saved auth state in standard per-user local paths:

- config: `~/.config/superset-cli/config.yaml`
- auth/browser state directory: `~/.local/share/superset-cli/`

Within the state directory, keep per-instance subdirectories for browser profile data and `storage-state.json`.

When the product identity changed from `superset-agent-cli` to `superset-cli`, move the defaults to the new paths as a breaking rename with no automatic fallback to the old directories.

## Consequences

- Local state is stable across CLI invocations and outside the repository working tree.
- Tests can override these paths with temporary directories without changing implementation structure.
- Existing local users must re-create or manually migrate config and auth state after the rename, because the CLI no longer falls back to the old `superset-agent-cli` paths.
- Future agents must treat these files as sensitive local artifacts and never commit them.

## Alternatives considered

### Store everything inside the repository

Rejected because repository-local state is easy to commit by mistake and couples machine-specific artifacts to source control.

### Require environment variables for every path

Rejected because the default user experience would become noisy and fragile. Optional overrides are enough for tests and special cases.
