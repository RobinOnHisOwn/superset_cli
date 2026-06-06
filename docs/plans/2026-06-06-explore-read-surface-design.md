# Design: Explore read surface

## Status

Research only. No code changes.

## What "Explore" is

Superset's Explore view is the chart-builder UI. The API exposes a read endpoint that returns the form-data ("explore state") used to render an Explore view for either a saved chart (by `slice_id`) or an ad-hoc combination of dataset + viz type.

Concretely:

- `GET /api/v1/explore/?slice_id=<id>` → returns the explore state for a saved chart.
- `GET /api/v1/explore/?datasource_id=<id>&datasource_type=table&viz_type=<viz>` → returns explore state for an ad-hoc combination.
- `GET /api/v1/explore/form_data/<key>` → resolves a saved form-data key back to explore state. (Closely related to the permalink-resolution commands already implemented.)

## Smallest useful CLI subset

Only the saved-chart form is worth adding now:

- `explore show <instance> --slice-id <id>` → calls `GET /api/v1/explore/?slice_id=<id>`.
- `explore form-data <instance> <key>` → calls `GET /api/v1/explore/form_data/<key>`.

Defer the ad-hoc datasource form. An agent that wants the result of a saved exploration can use `charts data` (which already runs the saved query); an agent that wants to inspect a permalink state already has `permalinks resolve`. The ad-hoc form is mostly useful when constructing new explorations, which is a write-shaped workflow.

## Relationship to existing commands

- `charts get` returns chart metadata; `explore show` returns the explore state for the same chart. They are complementary.
- `charts data` runs the saved query; `explore show` does not. They are not interchangeable.
- `permalinks resolve explore <key>` resolves dashboard/explore/sqllab permalinks; `explore form-data <key>` resolves the Explore-specific form-data key. There is overlap in spirit, but the underlying endpoint and payload shape differ enough that a separate command is justified.

## Output shape

- JSON: raw payload.
- Human: short summary including `datasource`, `viz_type`, and number of metrics/columns.

## Recommendation

Create one implementation follow-up ticket for both subcommands together. Splitting them would duplicate the new `explore` Typer group setup for very little benefit.

Follow-up ticket: `2026-06-06-explore-read-commands.md`.

## Decision follow-up

No durable decision change. The new `explore` command group remains strictly read-only and consistent with existing patterns.
