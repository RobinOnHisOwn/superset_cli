# Add security role read commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-security-read-surface-design.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Per the security read-surface design, expose read-only role list and detail commands as a thin pass-through to `/api/v1/security/role/`.

## Definition of done

- [ ] Client helpers wrap `GET /api/v1/security/role/` and `GET /api/v1/security/role/{pk}`.
- [ ] CLI commands `security roles list` and `security roles get` exist with JSON and human output.
- [ ] Tests cover JSON, human output, empty list, and not-found.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Strictly read-only. Do not include role create/update/delete.
