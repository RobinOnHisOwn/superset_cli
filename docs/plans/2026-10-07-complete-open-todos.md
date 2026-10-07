# Complete open Todos

**Date:** 2026-10-07

## Goal

Finish the remaining CLI cache controls and reconcile stale open tickets against verified implementations.

## Verified prerequisites and decisions

- Verified: origin/main already implements owner operations, list controls, timeout, API diagnostics, version/provenance, auth export, and the optional render recipe. Reuse these; do not rebuild them.
- Verified: Superset 6.1.0 chart-data GET accepts query parameter `force`; chart-data POST accepts top-level boolean `force`. QueryCacheManager bypasses reads and writes successful results back to the normal cache unless caching is disabled.
- Verified: SqlaTable.uid is `<numeric ID>__table`; CacheInvalidationRequestSchema accepts string `datasource_uids`. CacheRestApi uses CacheRestApi permissions and CSRF, removes tracked metadata, and can report 201 despite incomplete backend deletion.
- Proposed and selected under autonomous authority: opt-in `--cache-info` changes human output only; force refresh requires literal `--allow-write` because it intentionally replaces cached state. Existing non-force query overrides remain unchanged.
- Proposed and selected: targeted numeric dataset IDs only, deduplicated; verify the target OpenAPI schema before invalidation. Report acceptance, never invented eviction counts.
- Unknown: target deployment flags, permissions, backend alignment, and actual eviction. No live mutation authorized; explicitly leave live acceptance blocked.
- Optional CSV query selection: no recurring concrete use case supplied. Retain ADR 0012's existing CSV/JSON behavior; close the research ticket with a no-change outcome.

## Planned changes

1. Add failing transport-backed tests in `tests/test_cache_controls.py` for force GET/POST, multi-query preservation, cache diagnostics and unchanged JSON/CSV, guarded invalidation, schema validation, CSRF, failures, and no retries. Run and confirm failures.
2. Extend `client.py::get_chart_data` and `cli.py::charts_data` minimally; add `cache invalidate` using the shared client factory, write guard, and `_post` transport. Run focused tests after each implementation.
3. Update README, architecture map, ADR 0010's approved scope, and new ADR 0024. Record explicit compatibility limitations and absence of live eviction proof.
4. Verify existing open-ticket implementations with focused suites and optional synthetic Playwright/Chrome tests; validate the built wheel in isolation. Reconcile ticket state and repair historical conflict markers/private examples without pretending unperformed checks passed.
5. Inspect authoritative companion-skill source and update it in a separate worktree if needed; never edit deployed copies. Record any blocked external handoff explicitly.
6. Run full pytest, root/cache/chart help and safe guard smoke checks, build, documentation validation, and diff checks. No publication, commit, push, or live Superset writes.

## Verification

All development commands run after `cd /Users/robin.rittsteiger/worktrees/superset_cli/fix-open-todos` through `direnv exec` for that worktree. Run `uv run pytest tests/test_cache_controls.py -v`, broader regression suites, `uv run --with playwright pytest tests/test_dashboard_recipe.py -v`, `uv run pytest -v`, `uv run superset-cli --help`, and `uv build`. Keep isolated artifact/upgrade environments and research downloads under `/tmp`.

## Observed results

- TDD: new cache suite initially failed with 36 failures caused by missing controls; after implementation, cache/chart-output/override suites passed (90 tests). Version test failed on 0.2.0 before the 0.3.0 metadata update, then passed.
- Full `uv run pytest -v`: 996 passed, 13 optional browser tests skipped. Separate `uv run --with playwright pytest tests/test_dashboard_recipe.py -v`: all 14 passed against synthetic content using installed Chrome, including actual context loading and CSS-hidden failure checks.
- `uv build`: wheel and sdist built for 0.3.0. Isolated installed upgrade 0.1.0 -> published 0.2.0 -> built 0.3.0 verified command capabilities and unchanged synthetic auth/config checksums. PyPI metadata rechecked: latest is 0.2.0, so README's prior unpublished-0.2.0 statement was corrected. No publication.
- Root/chart/cache help and missing-opt-in smoke checks ran; both new guarded operations exited 1 naming the action and missing --allow-write without authentication access.
- Eighteen stale todo files were duplicates of existing completed tickets. Retain original completed records/evidence and delete only duplicate todo files; this also removes the conflicted/private-host cookie TODO without rewriting historical completed evidence. Two new tickets moved to done; targeted invalidation remains in-progress solely for explicitly authorized isolated live eviction acceptance.
- Shared companion source updated in its isolated worktree on `fix/superset-todo-recipes`; command ordering/capability/auth/render/cache recipes verified against mocked workflow and help. The prior source-owned `superset-api-troubleshooting` replacement was located on existing `docs/superset-open-todos`; do not overwrite another agent's work or patch the unmanaged deployed legacy copy. Integration/retirement/discovery remain operator rollout, not CLI implementation.
- `specdocs_validate` reports the pre-existing mismatch `docs/architecture/README.md` versus its expected `plan-*.md` convention; this repository intentionally uses its own documentation conventions. Pytest relative-link checks and explicit ticket/status/doc structure checks provide repository-native verification. Main checkouts remain untouched.
- Live Superset freshness/backend alignment, service-account permissions, and deployment/activation were not tested; no real credentials inspected and no live writes performed.

## Decision follow-up

Decision record update required: `docs/decisions/0024-targeted-cache-controls.md` and `docs/decisions/0010-write-scope-expansion.md`; preserve ADRs 0009, 0012, 0022, and 0023.
