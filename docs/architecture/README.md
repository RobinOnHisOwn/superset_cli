# Architecture overview

## System purpose and current scope

`superset-cli` is a Python CLI for self-hosted Apache Superset.

Current scope is read by default, write opt-in:
- manage local Superset instance configuration (add, list, remove)
- browser-cookie import login, remove local auth state, and inspect saved auth state
- read dashboards, charts, datasets, databases, annotation layers, CSS templates, themes, tags, reports, saved queries, queries, logs, permalinks, embedded dashboards, related objects, chart data, and the live OpenAPI spec
- write to charts, dashboards, datasets, databases, saved queries, SQL Lab, tags, themes, security roles/users/RLS, and asset-import surfaces
- every write command requires the literal `--allow-write` flag on every invocation per [ADR 0009](../decisions/0009-write-command-explicit-opt-in.md) and [ADR 0010](../decisions/0010-write-scope-expansion.md)
- paginate and refine list results with `--page` (0-based index), `--page-size`, `--search`, `--order-column`, and `--order-direction` CLI flags

This document explains how the current code is organized. For repository rationale, read `docs/decisions/`. For agent workflow rules, read `AGENTS.md`.

Keep this document current when command-to-code mappings, major module responsibilities, or common structural entry points change.

## Custom API entry point

`api INSTANCE PATH` maps to `api_request()` in `src/superset_cli/cli.py` and `SupersetClient.request()` / `validate_api_path()` in `src/superset_cli/client.py`; tests live in `tests/test_api.py`.
The CLI parses query/body options, invokes the shared write guard, validates saved auth, and performs at most one validated browser-cookie import before sending the custom request. The client confines paths to `/api/v1/`, disables redirects, and obtains CSRF for non-GET requests. Existing command flows are unchanged. See [ADR 0011](../decisions/0011-custom-api-authentication.md).

## High-level flow

Typical command flow:

1. The CLI entrypoint starts in `src/superset_cli/main.py`.
2. Typer command registration and command implementations live in `src/superset_cli/cli.py`.
3. Commands load configured instances through `src/superset_cli/config.py`.
4. Auth-related commands derive storage-state paths through `src/superset_cli/auth.py`, import cookies from an installed browser via `browser-cookie3`, and validate the imported session through `SupersetClient.get_current_user()`.
5. API-backed commands load validated saved browser state through `src/superset_cli/client.py`.
6. `SupersetClient` sends REST requests, fetching and caching Superset's CSRF token before writes, and returns JSON payloads.
7. `cli.py` formats those payloads for human-readable output or emits compact `--json` output.

## Source tree map

- `src/superset_cli/main.py` — process entrypoint
- `src/superset_cli/cli.py` — Typer app, command handlers, output formatting, guard checks
- `src/superset_cli/config.py` — config paths, load/save helpers, instance lookup/upsert
- `src/superset_cli/models.py` — Pydantic models for config data and URL validation
- `src/superset_cli/auth.py` — auth-state paths, auth inspection, browser login flow
- `src/superset_cli/client.py` — storage-state parsing, cookie header building, read-only Superset API client
- `tests/` — pytest coverage grouped by command area and helper module
- `docs/plans/` — plans and temporary implementation reasoning
- `docs/decisions/` — durable decision records
- `docs/architecture/` — structural documentation like this file

## Module responsibilities

### `main.py`

Provides the package entrypoint and delegates directly to the Typer app.

### `cli.py`

Owns the command-line interface:
- creates Typer sub-apps
- wires commands to helper modules
- enforces preconditions such as known instance names and existing auth state
- shapes output for human-readable and JSON modes
- handles API errors through the `_api_errors()` context manager, which catches `AuthExpiredError`, `NotFoundError`, and `httpx.RequestError` and prints a concise message then exits with code 1

Current command groups:
- `instances`
- `auth`
- `openapi`
- `me`
- `dashboards` (read + write)
- `charts` (read + write)
- `datasets` (read + write)
- `databases` (read + write)
- `permalinks`, `datasources`, `annotation-layers`, `css-templates`
- `themes` (read + write)
- `tags` (read + write)
- `reports`
- `saved-queries` (read + write)
- `queries`, `logs`
- `sqllab` (write-only group: execute, format-sql, estimate, stop-query)
- `security` (write-only group: roles, users, RLS via `security rls`)
- `import` (write-only group: server-side multipart asset bundles)

Write-command policy is enforced by the shared `_require_allow_write(...)` helper in `cli.py`. It is called by every write command before the API call. Without `--allow-write`, the command exits 1 with a message naming the would-be mutation and the missing flag, and no HTTP request is sent. Request bodies for write commands are loaded by the shared `_load_body(body, file)` helper, which accepts `--body '<json>'`, `--body -` (stdin), or `--file <path-to-json>`.

All four list commands (`dashboards list`, `charts list`, `datasets list`, `databases list`) accept optional `--page` (0-based integer), `--page-size`, `--search`, `--order-column`, and `--order-direction` flags. `--search` maps to each resource's primary name/title field using Superset contains filtering, while ordering flags forward directly into the Superset list query payload. When omitted, Superset applies its own defaults. The JSON output shape is unchanged regardless of whether these flags are supplied.

### `config.py`

Owns local config persistence:
- default config and state paths
- loading YAML config into models
- saving config back to disk
- inserting or replacing instances
- removing instances by name
- looking up instances by name

### `models.py`

Defines configuration models used by `config.py` and `cli.py`.
Currently this includes:
- `InstanceConfig`
- `Config`

It also normalizes and validates `base_url` values.

### `auth.py`

Owns auth-state helpers:
- derive storage-state paths per instance
- inspect saved auth state
- remove saved auth state for one instance
- import target-host cookies from installed browsers through `browser-cookie3`

`cli.py` completes login by validating each imported candidate against Superset. Auto mode continues past rejected browsers; explicit rejection or candidate exhaustion removes imported state. Network failures stop fallback and preserve state of unknown validity.

### `client.py`

Owns API access helpers:
- parse Playwright `storage-state.json`
- derive the outgoing `Cookie` header
- perform read-only Superset REST requests through `SupersetClient`
- raise `AuthExpiredError` on HTTP 401 or non-JSON (redirect-style auth failure) responses
- raise `NotFoundError` on HTTP 404 responses
- build Superset `q` query params for pagination, contains filters, and ordering via `build_list_params(...)`

`build_list_params` returns `{"q": json.dumps({...})}` with only the keys that were provided (non-None), or `{}` when no list-query args are set. The Superset API uses 0-based page indexing. For shared CLI search, the client emits a `filters` array with `{"col": ..., "opr": "ct", "value": ...}` and forwards explicit `order_column` / `order_direction` values.

Current API read methods:
- `get_current_user()` — returns the unwrapped user object (Superset wraps single-resource responses in `{"result": ...}`; these methods normalize that away)
- `get_openapi_spec()` — returns the raw OpenAPI schema payload from `/api/v1/_openapi`
- `list_dashboards(page, page_size, search, order_column, order_direction)` — returns the full list envelope `{"count": ..., "result": [...]}`. Optional list-query args are forwarded as `q` query params.
- `get_dashboard()` — returns the unwrapped dashboard object
- `get_dashboard_charts()` — returns the unwrapped chart list for one dashboard
- `get_dashboard_datasets()` — returns the unwrapped dataset list for one dashboard
- `list_charts(page, page_size, search, order_column, order_direction)` — returns the full list envelope
- `get_chart()` — returns the unwrapped chart object
- `list_datasets(page, page_size, search, order_column, order_direction)` — returns the full list envelope
- `get_dataset()` — returns the unwrapped dataset object
- `list_databases(page, page_size, search, order_column, order_direction)` — returns the full list envelope
- `get_database()` — returns the unwrapped database object
- `get_database_schemas(pk, catalog, force)` — returns the unwrapped schema list for one database
- `get_database_tables(pk, schema_name, catalog_name, force)` — returns the full table envelope for one database schema

Single-resource getters (`get_*`) unwrap the Superset `{"result": ...}` envelope before returning, so callers receive the resource dict directly. List methods (`list_*`) return the full envelope so callers can access both `count` and `result`.

Current API write methods (require CLI `--allow-write` per ADR 0009/0010):
- `create_chart(body)`, `update_chart(pk, body)`, `delete_chart(pk)`, `favorite_chart(pk)`, `unfavorite_chart(pk)`
- `create_dashboard(body)`, `update_dashboard(id_or_slug, body)`, `delete_dashboard(id_or_slug)`, `favorite_dashboard(id_or_slug)`, `unfavorite_dashboard(id_or_slug)`, `copy_dashboard(id_or_slug, body)`
- `create_dataset(body)`, `update_dataset(pk, body)`, `delete_dataset(pk)`, `refresh_dataset(pk)`
- `create_database(body)`, `update_database(pk, body)`, `delete_database(pk)`, `test_database_connection(body)`
- `create_saved_query(body)`, `update_saved_query(pk, body)`, `delete_saved_query(pk)`
- `execute_sql(body)`, `format_sql(body)`, `estimate_sql(body)`, `stop_sql_query(body)`
- `create_tag(body)`, `update_tag(pk, body)`, `delete_tag(pk)`
- `create_theme(body)`, `update_theme(pk, body)`, `delete_theme(pk)`
- `create_role(body)`, `update_role(pk, body)`, `delete_role(pk)`
- `create_user(body)`, `update_user(pk, body)`, `delete_user(pk)`
- `create_rls_rule(body)`, `update_rls_rule(pk, body)`, `delete_rls_rule(pk)`
- `import_assets(resource, *, file_path, passwords=None, overwrite=False)` — multipart upload of a Superset asset bundle ZIP

Writes route through `_post`, `_put`, `_delete`, which fetch `/api/v1/security/csrf_token/` once per client and send its result as `X-CSRFToken`. They share the same response-handling path as `_get` via `_handle_response`. A successful response with no body returns `{}`.

## Command-to-code map

All write commands are implemented in `src/superset_cli/cli.py` against methods on `src/superset_cli/client.py`. Their tests live in `tests/test_writes.py` (parametrized across every write command) and exercise both the missing-`--allow-write` refusal path and the success path.

### Global CLI

- `superset-cli --help`
  - code: `src/superset_cli/main.py`, `src/superset_cli/cli.py`
  - tests: `tests/test_cli.py`

### Instances commands

- `instances list`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/config.py`
  - tests: `tests/test_cli.py`, `tests/test_instances_add.py`

- `instances add <name> <base_url>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/config.py`, `src/superset_cli/models.py`
  - tests: `tests/test_instances_add.py`, `tests/test_config.py`

- `instances remove <name>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/config.py`
  - tests: `tests/test_instances_remove.py`

### Auth commands

- `auth login <instance> [--browser ...]`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/auth.py`, `src/superset_cli/config.py`
  - tests: `tests/test_auth.py`
  - notes: reads cookies for the instance host from installed browsers via `browser-cookie3`, writes each candidate to `storage-state.json`, and validates it through `/api/v1/me/` before reporting success. `--browser` choices: `auto` (default), `chrome`, `edge`, `brave`, `firefox`, `zen`, `safari`. `auto` tries each browser in priority order and picks the first candidate accepted by Superset; explicit browser selection remains fail-fast. See [ADR 0008](../decisions/0008-cookie-extraction-from-installed-browsers.md) for the rationale.

- `auth logout <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/auth.py`
  - tests: `tests/test_auth_logout.py`

- `auth status <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/auth.py`, `src/superset_cli/client.py`
  - tests: `tests/test_auth_status.py`, `tests/test_client.py`

- `auth validate <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_auth_validate.py`

### OpenAPI commands

- `openapi fetch <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_openapi.py`

### Current-user metadata commands

- `me show <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_me.py`

- `me roles <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_me.py`

### Permalink commands

- `permalinks resolve <instance> <kind> <key>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_phase2_special_reads.py`

### Datasource commands

- `datasources column-values <instance> <type> <id> <column>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_phase2_special_reads.py`

### Annotation-layer commands

- `annotation-layers list <instance>`, `annotation-layers get <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_annotation_layers.py`

### CSS-template commands

- `css-templates list <instance>`, `css-templates get <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_css_templates.py`

### Theme commands

- `themes list <instance>`, `themes get <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_themes.py`

### Tag commands

- `tags list <instance>`, `tags get <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_tags.py`

### Report-schedule commands

- `reports list <instance>`, `reports get <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_reports.py`

### Saved-query commands

- `saved-queries list <instance>`, `saved-queries get <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_saved_queries.py`

### Query-history commands

- `queries list <instance>`, `queries get <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_queries.py`

### Log and recent-activity commands

- `logs list <instance>`, `logs get <instance> <pk>`, `logs recent-activity <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_logs.py`

### Dashboard commands

- `dashboards list <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_dashboards.py`

- `dashboards get <instance> <id_or_slug>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_dashboards_get.py`

- `dashboards charts <instance> <id_or_slug>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_dashboards_get.py`

- `dashboards datasets <instance> <id_or_slug>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_dashboards_get.py`

- `dashboards embedded <instance> <id_or_slug>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_phase2_special_reads.py`

### Charts commands

- `charts list <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_charts.py`

- `charts get <instance> <id_or_uuid>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_charts_get.py`

- `charts data <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_chart_data.py`

### Datasets commands

- `datasets list <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_datasets.py`

- `datasets get <instance> <id_or_uuid>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_datasets_get.py`

- `datasets related <instance> <id_or_uuid>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_phase2_special_reads.py`

### Databases commands

- `databases list <instance>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_databases.py`

- `databases get <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_databases_get.py`

- `databases schemas <instance> <pk>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_databases_get.py`

- `databases tables <instance> <pk> --schema <schema>`
  - code: `src/superset_cli/cli.py`, `src/superset_cli/client.py`
  - tests: `tests/test_databases_get.py`

## Test map

- `tests/test_cli.py` — top-level help and empty `instances list`
- `tests/test_config.py` — config loading behavior
- `tests/test_client.py` — storage-state parsing, cookie header formatting, and shared client helpers
- `tests/test_instances_add.py` — instance persistence and visibility in JSON output
- `tests/test_instances_remove.py` — instance removal from config, isolation from auth state
- `tests/test_auth.py` — auth login preconditions and browser-login handoff
- `tests/test_auth_logout.py` — auth logout preconditions and auth state directory removal
- `tests/test_auth_status.py` — auth-state existence checks and status payload
- `tests/test_auth_validate.py` — current-user validation flow
- `tests/test_openapi.py` — OpenAPI spec fetch flow
- `tests/test_me.py` — current-user metadata reads
- `tests/test_dashboards.py` — dashboard list flow
- `tests/test_dashboards_get.py` — dashboard detail flow and dashboard-related chart/dataset reads
- `tests/test_charts.py` — chart list flow
- `tests/test_charts_get.py` — chart detail flow
- `tests/test_datasets.py` — dataset list flow
- `tests/test_datasets_get.py` — dataset detail flow
- `tests/test_databases.py` — database list flow
- `tests/test_databases_get.py` — database detail flow and schema/table discovery reads
- `tests/test_annotation_layers.py`, `tests/test_css_templates.py`, `tests/test_themes.py`, `tests/test_tags.py`, `tests/test_reports.py`, `tests/test_saved_queries.py`, `tests/test_queries.py`, `tests/test_logs.py` — list/get read flows for the eight Phase 1 resources
- `tests/test_phase2_special_reads.py` — embedded dashboard, permalink resolution, dataset related-objects, and datasource column-values
- `tests/test_chart_data.py` — saved chart data fetch
- `tests/test_auth_relogin.py` — combined logout-then-login flow
- `tests/test_writes.py` — every write command: parametrized refusal without `--allow-write`, success path with `--allow-write`, `--json` output shape, body/file loading, and import-specific validation

## Typical change entry points

### Add a new write command

Start with:
- `src/superset_cli/cli.py` — register the command on the right Typer sub-app and call `_require_allow_write(allow_write, action=...)` before `_run_write(...)`
- `src/superset_cli/client.py` — add the matching `_post` / `_put` / `_delete` method
- `tests/fakes.py` — add a matching no-op method that records into `self.calls` via `self._record(...)`
- `tests/test_writes.py` — add a case to `WRITE_CASES`
- update this file and `README.md` if the public surface changes

### Add a new read-only resource command

Start with:
- `src/superset_cli/cli.py`
- `src/superset_cli/client.py`
- a new or nearby test in `tests/`

### Change output formatting or JSON shape

Start with:
- `src/superset_cli/cli.py`
- the command-specific test file
- `README.md` if command examples or output contracts change

### Change config storage behavior

Start with:
- `src/superset_cli/config.py`
- `src/superset_cli/models.py`
- `tests/test_config.py`
- `tests/test_instances_add.py`

### Change auth-state behavior or browser login flow

Start with:
- `src/superset_cli/auth.py`
- `src/superset_cli/client.py`
- `tests/test_auth.py`
- `tests/test_auth_status.py`
- `tests/test_auth_validate.py`

### Change API error handling or user-facing error messages

Start with:
- `src/superset_cli/client.py` — `AuthExpiredError`, `NotFoundError`, `_get()` mapping logic
- `src/superset_cli/cli.py` — `_api_errors()` context manager
- `tests/test_client.py` — unit tests for exception mapping
- the command-specific test file for CLI-level message/exit-code tests

## Related docs

- Project overview: `README.md`
- Agent workflow rules: `AGENTS.md`
- Durable rationale: `docs/decisions/README.md`
- Plan/process guidance: `docs/plans/README.md`
