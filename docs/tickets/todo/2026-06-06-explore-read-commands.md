# Add Explore read commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-explore-read-surface-design.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Per the Explore read-surface design, expose two narrow read commands for explore state.

## Definition of done

- [ ] Client helpers wrap `GET /api/v1/explore/?slice_id=<id>` and `GET /api/v1/explore/form_data/<key>`.
- [ ] CLI commands `explore show <instance> --slice-id <id>` and `explore form-data <instance> <key>` exist with JSON and human output.
- [ ] Tests cover JSON, human output, missing parameters, and not-found.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Strictly read-only. Do not include the ad-hoc datasource form or any explore mutation.
