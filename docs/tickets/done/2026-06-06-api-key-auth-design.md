# Research version-gated API-key auth support

- Status: done
- Priority: medium
- Type: research
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `src/superset_cli/config.py`, `README.md`, `docs/architecture/README.md`

## Context

This CLI currently relies only on saved browser sessions. API-key auth appears in unreleased Superset Next documentation, but it is not yet verified as a stable OSS capability for the versions this repository is likely to target. Before designing local config or CLI behavior around API keys, the repository should confirm version support and decide how to gate any future implementation.

## Definition of done

- [x] The Superset versions that do or do not support API-key auth are documented with concrete doc or release evidence.
- [x] The repository's target-version assumptions for any API-key work are documented.
- [x] If API-key auth is worth pursuing, the desired CLI contract is outlined, including config shape, secret handling, and auth-mode selection.
- [x] Follow-up work is either linked to a version-gated implementation ticket or explicitly deferred.

## Notes

Do not assume API-key auth is available on current stable Superset OSS without version-specific verification.
