# Superset client pagination param builder

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/client.py`, `tests/test_client.py`, `docs/architecture/README.md`

## Context

Superset pagination query building is already implemented through `build_list_params`. The helper translates optional page and page-size values into the JSON `q` query structure expected by the Superset API.

## Definition of done

- [x] No pagination arguments produce an empty dict.
- [x] Provided pagination arguments are serialized under a `q` key as JSON.
- [x] `None` values are omitted from the serialized query payload.

## Notes

The current API convention uses 0-based page indexing.
