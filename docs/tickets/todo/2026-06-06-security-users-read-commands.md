# Add security user read commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-security-read-surface-design.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Per the security read-surface design, expose read-only user list and detail commands as a thin pass-through to `/api/v1/security/user/` (where exposed by the FAB version on the target Superset).

## Definition of done

- [ ] Client helpers wrap `GET /api/v1/security/user/` and `GET /api/v1/security/user/{pk}`.
- [ ] CLI commands `security users list` and `security users get` exist with JSON and human output.
- [ ] Tests cover JSON, human output, empty list, and not-found.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Strictly read-only. Do not include user create/update/delete or password operations. Surface only fields that the authenticated user already sees in the Superset UI.
