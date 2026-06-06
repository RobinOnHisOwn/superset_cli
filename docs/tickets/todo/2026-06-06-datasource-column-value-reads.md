# Add datasource column-value read commands

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes a read endpoint for datasource column values, but the CLI currently cannot inspect those values directly. This is a useful read-only feature for agent-assisted filtering, debugging, and lightweight data exploration without taking on full SQL Lab scope.

## Definition of done

- [ ] A CLI command exposes datasource column-value reads with the required datasource identifiers and column name inputs.
- [ ] Client helpers wrap the corresponding Superset datasource read endpoint.
- [ ] Tests cover param forwarding, output modes, and standard guard paths.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep this ticket limited to value lookup. Do not include datasource expression validation or broader datasource mutation.
