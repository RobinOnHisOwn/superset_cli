# Charts get command

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_agent_cli/cli.py`, `src/superset_agent_cli/client.py`, `tests/test_charts_get.py`, `docs/architecture/README.md`

## Context

`charts get <instance> <id_or_uuid>` is already implemented. It fetches a single chart object and formats it for JSON or concise human-readable display.

## Definition of done

- [x] The command rejects unknown instances and missing auth state.
- [x] `--json` returns the unwrapped chart object.
- [x] Human output shows chart ID, name, and viz type while not-found and network errors are surfaced clearly.

## Notes

The same client error-handling pattern used by other resource getters applies here.
