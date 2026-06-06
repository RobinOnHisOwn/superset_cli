# Phase 2: special-shape read commands

## Goal

Add four read commands that don't share the standard list+get shape: embedded dashboard, permalink resolution, dataset related-objects, and datasource column values.

## Tickets covered

- `2026-06-06-embedded-dashboard-read-commands.md`
- `2026-06-06-permalink-resolution-reads.md`
- `2026-06-06-dataset-related-objects.md`
- `2026-06-06-datasource-column-value-reads.md`

## API mappings

- Embedded dashboard config: `GET /api/v1/dashboard/{pk}/embedded` → adds `dashboards embedded <id_or_slug>`.
- Permalink resolution:
  - `GET /api/v1/dashboard/permalink/{key}`
  - `GET /api/v1/explore/permalink/{key}`
  - `GET /api/v1/sqllab/permalink/{key}`
  - Single command group `permalinks resolve <kind> <key>` where `kind` is one of `dashboard`, `explore`, `sqllab`.
- Dataset related objects: `GET /api/v1/dataset/{id}/related_objects` → adds `datasets related <id>`.
- Datasource column values: `GET /api/v1/datasource/{type}/{id}/column/{column}/values/` → adds `datasources column-values <type> <id> <column>`.

## Plan

1. Add client helpers: `get_dashboard_embedded`, `get_permalink(kind, key)`, `get_dataset_related_objects(id)`, `get_datasource_column_values(type, id, column)`.
2. Add `dashboards embedded` under existing dashboards group; add `datasets related` under existing datasets group; create new `permalinks` and `datasources` groups for the other two.
3. Tests cover JSON, human output, not-found.
4. Update fakes and docs once at end of phase.

## Decision follow-up

No durable decision change.
