# Add row-level-security read commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-security-read-surface-design.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Per the security read-surface design, expose read-only row-level-security rules.

## Definition of done

- [ ] Client helpers wrap `GET /api/v1/rowlevelsecurity/` and `GET /api/v1/rowlevelsecurity/{pk}`.
- [ ] CLI commands `security rls list` and `security rls get` exist with JSON and human output.
- [ ] Tests cover JSON, human output, empty list, and not-found.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Strictly read-only. Do not include RLS rule creation, update, or deletion.
