# Design the Explore read surface

- Status: done
- Priority: medium
- Type: research
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes an Explore read endpoint, but the CLI currently has no Explore command group. Because Explore data can be broad and may overlap with chart-data or permalink workflows, the repository should first define the smallest useful Explore read surface before implementation.

## Definition of done

- [x] The specific Explore read use cases worth exposing in the CLI are identified.
- [x] The expected inputs, output shape, and relationship to chart-data and permalink commands are documented.
- [x] A recommended initial CLI contract is captured in a short plan.
- [x] Follow-up implementation tickets exist for the approved subset.

## Notes

Keep this work read-only and avoid expanding into broader query-execution behavior.
