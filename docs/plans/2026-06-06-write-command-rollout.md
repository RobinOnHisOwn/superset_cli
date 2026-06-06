# Write-command rollout

- Status: complete
- Date: 2026-06-06
- Related tickets: `docs/tickets/todo/2026-06-06-write-scope-expansion-decision.md`, `docs/tickets/todo/2026-06-06-chart-write-commands.md`, `docs/tickets/todo/2026-06-06-dashboard-write-commands.md`, `docs/tickets/todo/2026-06-06-database-write-commands.md`, `docs/tickets/todo/2026-06-06-dataset-write-commands.md`, `docs/tickets/todo/2026-06-06-saved-query-write-commands.md`, `docs/tickets/todo/2026-06-06-sqllab-write-commands.md`, `docs/tickets/todo/2026-06-06-security-admin-write-commands.md`, `docs/tickets/todo/2026-06-06-tags-and-themes-write-commands.md`, `docs/tickets/todo/2026-06-06-asset-import-write-commands.md`
- Related decisions: [`0001-read-only-bootstrap-scope`](../decisions/0001-read-only-bootstrap-scope.md), [`0009-write-command-explicit-opt-in`](../decisions/0009-write-command-explicit-opt-in.md)

## Goal

Bulk-deliver the nine write-command tickets the user approved in one rollout. Land:

1. ADR 0010 expanding scope from read-only to read+write, listing the approved write surface per resource and the safety contract.
2. Shared `--allow-write` helper in `cli.py`. Required by every write command (per ADR 0009).
3. `_post`, `_put`, `_delete` on `SupersetClient`.
4. Resource client methods + matching fakes for chart, dashboard, dataset, database, saved-query, SQL Lab, tag, theme, security/admin, and asset-import surfaces.
5. CLI commands for each resource with `--allow-write` enforced via the shared helper.
6. Tests per resource: at minimum unknown-instance, missing-storage-state, missing `--allow-write` (dry-run exit non-zero), `--allow-write` success path, `--json` output shape.
7. README + `docs/architecture/README.md` updates.

## Approved write surface (binds ADR 0010)

Pragmatic, opinionated subset. Each resource gets create/update/delete plus the most commonly used resource-specific actions. Exotic endpoints are out of scope and can be added per-ticket later.

- **charts**: create, update, delete, favorite, unfavorite
- **dashboards**: create, update, delete, favorite, unfavorite, copy
- **datasets**: create, update, delete, refresh
- **databases**: create, update, delete, test-connection
- **saved-queries**: create, update, delete
- **sqllab**: execute, format-sql, estimate, stop-query
- **tags**: create, update, delete
- **themes**: create, update, delete
- **security**: roles create/update/delete, users create/update/delete, RLS rules create/update/delete
- **import**: dashboard, chart, dataset, database, saved-query bundles via multipart upload

All commands require explicit `--allow-write` on every invocation (ADR 0009). No exceptions.

## Test strategy

Every write command gets at least:

- one test: missing `--allow-write` -> exit 1 with the "would mutate, re-run with --allow-write" message and no client method called.
- one test: with `--allow-write` -> success, fake client method invoked with expected args, JSON shape preserved.

Existing read commands stay unchanged. The shared helper is the one place the policy lives, so unit tests for the helper itself cover the contract.

## Out of scope this rollout

- Backward-compatibility shims for the no-longer-true "read-only bootstrap" framing in README — read-only framing is updated to "read by default, write opt-in".
- Per-resource niche endpoints (warm-up, cache-screenshot, embedded-config beyond delete, certified-by helpers). Tickets can be opened later if needed.
- Live verification against a real Superset. Local fake-driven tests + `uv build` + `--help` smoke are the verification bar for this rollout.

## Decision follow-up

Decision record update required:
- `docs/decisions/0001-read-only-bootstrap-scope.md` — mark superseded by 0010
- `docs/decisions/0010-write-scope-expansion.md` — new, captures approved surface
