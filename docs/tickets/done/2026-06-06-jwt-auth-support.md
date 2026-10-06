# Add direct JWT auth support

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/tickets/todo/2026-06-06-jwt-auth-design.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `src/superset_cli/config.py`, `README.md`, `docs/architecture/README.md`

## Context

The CLI currently depends on browser session cookies for API access. Superset also documents direct JWT login and refresh flows, which could help in simpler deployments that support credential-based API auth.

## Definition of done

- [x] The approved JWT auth contract is implemented in config, client, and CLI layers.
- [x] The CLI can authenticate and refresh access using the documented Superset JWT endpoints for supported setups.
- [x] Tests cover happy paths, refresh behavior, and failure handling.
- [x] `README.md` and `docs/architecture/README.md` document JWT auth setup and limitations.

## Completion evidence

DB/LDAP lifecycle, per-instance mode, private atomic token storage, bearer/TLS validation, metadata-only status, GET-only refresh, and no sent-write retries are covered. Existing browser state is preserved. Superset modifying APIs still require CSRF: the older no-CSRF design claim was corrected against source. Tests are synthetic; no live JWT deployment login was performed. See [continuation evidence](../../plans/2026-10-06-autonomous-todos-continuation.md) and ADR 0018.

## Notes

Implement this only after the JWT auth contract is designed.
