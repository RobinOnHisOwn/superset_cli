# Base URL validation and normalization

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/models.py`, `src/superset_cli/config.py`, `src/superset_cli/cli.py`, `docs/architecture/README.md`

## Context

Instance URL validation is already implemented in `InstanceConfig`. Base URLs are validated as HTTP URLs and normalized to remove trailing slashes before storage and use.

## Definition of done

- [x] `InstanceConfig.base_url` is validated through Pydantic URL handling.
- [x] Normalized URLs are converted back to strings for config persistence and client use.
- [x] Trailing slashes are removed during normalization.

## Notes

This behavior is visible directly in `models.py`.
