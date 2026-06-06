# Design read-only export commands

- Status: done
- Priority: medium
- Type: research
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes export endpoints for several read-only asset types, but the CLI currently has no export workflow. Export commands are attractive for agents, yet they raise interface questions around file paths, binary responses, stdout behavior, and whether multiple resource types should share one command pattern.

## Definition of done

- [x] The most useful initial export endpoints are identified from the current Superset API surface.
- [x] A recommended CLI contract is proposed for file output, destination handling, and error behavior.
- [x] Risks to current JSON and human-output expectations are documented.
- [x] Follow-up implementation tickets exist for the approved export commands.

## Notes

Keep the work read-only. Do not include import or other write-capable asset operations.
