# Phase 1: list + get read commands for 8 resources

## Goal

Add read-only `list` and `get` CLI commands for 8 Superset resources that share the same shape, using one shared implementation pattern.

## Tickets covered

- `2026-06-06-annotation-layer-read-commands.md`
- `2026-06-06-css-template-read-commands.md`
- `2026-06-06-theme-read-commands.md`
- `2026-06-06-tags-read-commands.md`
- `2026-06-06-report-schedule-read-commands.md`
- `2026-06-06-saved-queries-read-commands.md`
- `2026-06-06-query-history-read-commands.md`
- `2026-06-06-logs-and-recent-activity-reads.md`

## API mappings

| Resource | List endpoint | Detail endpoint | Search column |
|---|---|---|---|
| annotation-layers | `/api/v1/annotation_layer/` | `/api/v1/annotation_layer/{pk}` | `name` |
| css-templates | `/api/v1/css_template/` | `/api/v1/css_template/{pk}` | `template_name` |
| themes | `/api/v1/theme/` | `/api/v1/theme/{pk}` | `theme_name` |
| tags | `/api/v1/tag/` | `/api/v1/tag/{pk}` | `name` |
| reports | `/api/v1/report/` | `/api/v1/report/{pk}` | `name` |
| saved-queries | `/api/v1/saved_query/` | `/api/v1/saved_query/{pk}` | `label` |
| queries | `/api/v1/query/` | `/api/v1/query/{pk}` | `sql` |
| logs | `/api/v1/log/` | `/api/v1/log/{pk}` | (none) |

## Plan

1. Extend `SupersetClient` with one `list_<x>()` and one `get_<x>()` per resource, reusing `build_list_params` for paging/search/order.
2. Add a new Typer subgroup per resource in `cli.py`, each with `list` and `get` commands.
3. Reuse the existing `_api_errors()` guard, `_require_instance`, and `_require_storage_state`.
4. Add per-resource fake methods in `tests/fakes.py`.
5. Add one focused CLI test file per resource covering JSON output, human output for both `list` and `get`, plus a `not_found` guard. Standard auth / network / closure paths are already exercised across the suite.
6. Add an `client.py` unit test per resource confirming `list_*` forwards page params and `get_*` unwraps `result`.
7. Update `README.md` and `docs/architecture/README.md` once at the end.

## Tests

- `tests/test_annotation_layers.py`
- `tests/test_css_templates.py`
- `tests/test_themes.py`
- `tests/test_tags.py`
- `tests/test_reports.py`
- `tests/test_saved_queries.py`
- `tests/test_queries.py`
- `tests/test_logs.py`
- Additional `client.py` cases in `tests/test_client.py`.

## Decision follow-up

No durable decision change. All eight stay strictly within the read-only bootstrap scope in `docs/decisions/0001-read-only-bootstrap-scope.md`.
