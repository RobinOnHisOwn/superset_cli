# Add dataset related-objects inspection

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_datasets_get.py`, `README.md`, `docs/architecture/README.md`

## Context

Datasets currently support only list and detail reads. Superset also exposes a read-only endpoint for the charts and dashboards associated with a dataset. That relationship is useful for impact analysis and for agent navigation from a table to the assets that depend on it.

## Definition of done

- [ ] A client helper exists for `/api/v1/dataset/{id_or_uuid}/related_objects`.
- [ ] A CLI command exposes the related-objects payload in human and JSON modes.
- [ ] Tests cover happy-path output plus unknown-instance, missing-auth, and not-found behavior.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Keep the JSON output close to the Superset payload unless there is a strong reason to reshape it.
