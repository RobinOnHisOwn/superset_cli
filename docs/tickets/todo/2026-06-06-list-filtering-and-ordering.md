# Add list filtering and ordering to resource list commands

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_dashboards.py`, `tests/test_charts.py`, `tests/test_datasets.py`, `tests/test_databases.py`, `README.md`, `docs/architecture/README.md`

## Context

All current list commands expose only `--page` and `--page-size`, even though Superset list endpoints support richer read-side query controls through the `q` payload. The CLI should expose a small shared set of filter and ordering flags for dashboards, charts, datasets, and databases without changing the existing `--json` response shape.

## Definition of done

- [ ] Shared list-query flags for filtering and ordering exist on `dashboards list`, `charts list`, `datasets list`, and `databases list`.
- [ ] The client builds and forwards the corresponding Superset `q` params consistently.
- [ ] Tests cover forwarded params plus preserved human and JSON output behavior.
- [ ] `README.md` and `docs/architecture/README.md` document the new flags.

## Notes

Start with the smallest useful contract, such as one search-like filter plus explicit ordering flags, rather than mirroring the entire Superset query DSL at once.
