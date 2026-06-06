# Storage-state loading helper

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/client.py`, `tests/test_client.py`

## Context

Playwright storage-state parsing is already implemented through `load_storage_state`. The helper reads JSON from disk and validates it into the local `StorageState` model.

## Definition of done

- [x] `load_storage_state` reads `storage-state.json` from disk.
- [x] Cookie entries are validated into typed `Cookie` records.
- [x] Tests verify that parsed cookie values are accessible through the returned model.

## Notes

This helper is used by both auth inspection and the Superset client.
