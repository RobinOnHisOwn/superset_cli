# Complete remaining open todos

**Date:** 2026-10-06

## Goal

Finish actionable local backlog without duplicating completed origin/main work, changing existing defaults/contracts, or guessing server capabilities.

## Verified prerequisites

- Implementation uses isolated `fix/open-todos-chart-docs`, based on freshly fetched remote main; timeout work remains intact.
- Existing `_list_resource`, `build_list_params`, and `_run_list` provide the shared extension point. Primary and security lists now use it consistently.
- FAB source verifies `q.filters`, `q.columns`, count/IDs and list/order metadata; invalid columns can be silently pruned, so projection requires capability validation.
- `_info` advertises filters/operators, not list/order columns. Superset 6.1.0 charts do not advertise ID ordering. The log API omits `_info` entirely but advertises `dttm` search; FAB 5.2.2 supports datetime `gt`/`lt`, not a universal `ge`.
- API-key support was initially unknown. Corrected concrete inheritance verifies Superset 6.1.0 plus FAB 5.2.2 with enabled/initialized key support. Deployment capability and actual credential acceptance remain runtime prerequisites, checked before persisting a binding; no target was probed.
- Shared skill sources are in an isolated `docs/superset-open-todos` source worktree. The unmanaged legacy workaround had no source registration; its new authoritative replacement has a distinct name and requires operator rollout.

## Implementation and outcomes

1. Imported the three local list tickets and query-selection research ticket; resolved all actionable tickets and moved them to done.
2. Added failing list tests first, then repeatable typed JSON-object `--filter`, repeatable `--columns`, and opt-in `--all` across all 15 paginated lists. New controls preserve ordinary output, page, ordering, and auth defaults.
3. Aggregate only after count/identity/duplicate/progress checks pass; retain server caps and advertised ordering. Buffer results in memory and explicitly disclaim atomic snapshot isolation. Do not add ID to a projection.
4. Validate filters through `_info` and columns through list metadata. A source-verified missing log `_info` led to failing regression tests, then a 404-only native list-validation fallback. Permission/malformed-metadata failures still fail closed.
5. Evaluate multi-query fixtures and existing JSON indexing: no recurring selection need established, so optional query-index remains unimplemented. Preserve ADR 0012 and whole-payload exit status; close the research ticket with a no-change decision.
6. Add environment-bound API-key mode after correcting upstream research. Read-validate before saving only environment name/prefix. Require safe Bearer syntax and HTTPS except loopback; never follow redirects, extract cookies, fall back to another auth mode, persist keys, or replay a sent mutation. Preserve CSRF/write guards. Additional failing tests fixed browser logout accidentally deleting preserved state, clear resetting another selected mode, and misleading browser-login advice on API-key HTML replies.
7. Refresh authoritative companion skill and add `superset-api-troubleshooting`; update its catalog. Mocked workflow covers discovery, validation, guarded context clearing, object/data reads, diff, and custom API without manual cookie extraction. No deployed files or unrelated source branch were changed.
8. Update README, architecture, decision index, research, plans, and tickets. No dependency, packaging, environment, or CLI-default changes; no staging, commits, pushes, PRs, or live Superset requests.

## Pre-commit review follow-up

Independent review identified FAB 5.2.2's JSON `q` fallback running `parse_qs` after Flask already decoded the parameter. This can alter literal `+`/`%` or split on `&`. Verify against the version-pinned API source, add failing HTTP round-trip regressions (both search and typed filters, including checked pagination), then encode those characters as JSON Unicode escapes in the existing `build_q_params` helper. JSON decoders preserve the original values without adding a dependency, changing public JSON output, or introducing another transport. Inspect every caller and rerun focused/full checks before staging.

Completed with sixteen parameterized regressions: eight string round trips failed initially; six additional numeric/nested cases reproduced the naive replacement corrupting positive float exponents. The final small token-aware regex rewrites entire JSON string tokens and normalizes numeric `e+` to `e`, preserving finite JSON values for both ordinary JSON and FAB decoding, including `--all` reserialization. Focused client/list tests: **119 passed**. Independent follow-up review found no remaining concrete blocker; it did not execute tests.

The divergent human branch named `origin/main` is not the remote main; use explicit `refs/remotes/origin/main`. Imported ticket names are intentional, not a reason to incorporate unrelated human history. API-key `set` explicitly replaces auth selection/bindings; `clear` returns to cookies, preserving auth files but not restoring earlier JWT credential bindings, as documented. No implicit auth-mode restoration is added during review.

## Verification evidence

Commands use `direnv exec "$PWD"` in the CLI worktree:

- Initial list tests: **45 failed, 11 passed**, then **56 passed**. Four malformed-metadata regressions failed before guards; log `_info` fallback regressions produced **2 expected failures** before the shared fix.
- Initial API-key command tests failed on the absent command; targeted regressions reproduced the state-preservation and diagnostic faults before fixing them.
- Focused list/API-key/skill/chart-data/docs-link command: `uv run pytest tests/test_api_key_auth.py tests/test_list_controls.py tests/test_skill_recipes.py tests/test_chart_data.py tests/test_docs_links.py -q --tb=short` — **105 passed** before the final four regressions were added; the final full run includes them.
- Full run before review: `uv run pytest -v` — **930 passed, 13 skipped**; log `/tmp/superset-all-todos-final-pytest.log`.
- Final pre-commit `uv run pytest -v` — **946 passed, 13 skipped**; log `/tmp/superset-precommit-final-pytest.log`. Rebuilt wheel/source distribution and reran root help and both diff checks successfully after the reviewed fix.
- `uv build` — built source distribution and wheel successfully.
- `uv run superset-cli --help`, `charts list --help`, and `auth api-key set --help` — all exit zero; confirm root timeout, list controls, API-key binding and prefix options.
- Malformed-filter manual smoke with an absent temporary config — exits **2** during option parsing, without network/credential access.
- Shared source checks — both skills have valid YAML frontmatter, Requirements, corrected instance examples, safe neutral examples, and existing catalog links.
- `git diff --check` — clean in both source worktrees.
- Repository doc-link tests — pass as part of the full suite. `specdocs_validate` has a pre-existing original-workspace filename-pattern error for `docs/architecture/README.md`; do not rename the repository's canonical document to satisfy an unrelated validator convention.

## Changed files

CLI source worktree: `~/worktrees/superset_cli/fix-open-todos-chart-docs`.

- `src/superset_cli/cli.py`, `client.py`, `jwt_auth.py`, `models.py`, and new `api_key_auth.py`.
- New `tests/test_timeout.py`, `test_list_controls.py`, `test_api_key_auth.py`, and `test_skill_recipes.py`.
- `README.md`, `docs/architecture/README.md`, `docs/decisions/README.md`, new ADRs 0021–0023, corrected API-key research, timeout/remaining-todos plans, and seven completed tickets.

Shared skill source worktree: `docs/superset-open-todos`; changed `README.md`, `skills/datateam/superset-cli/SKILL.md`, and new `skills/datateam/superset-api-troubleshooting/SKILL.md`.

Post-documentation check: `uv run pytest tests/test_docs_links.py tests/test_api_key_auth.py tests/test_list_controls.py tests/test_skill_recipes.py -q --tb=short` — **82 passed**. Both diff checks were clean and the implementation worktree contained **zero** todo/in-progress Markdown tickets.

## Remaining risks and handoff

- The 13 existing opt-in/browser integration tests remain skipped. Real API-key issuance/configuration/RBAC/CSRF and browser rendering were not tested; source/mock evidence is not live compatibility proof.
- List aggregation is not an atomic snapshot and uses memory proportional to the complete result.
- Source changes are uncommitted. Integration/publication, deploying/reloading the shared skills, and retiring the unmanaged legacy skill are operator handoff, not completed deployment claims.
- Consulted decisions: ADRs 0009, 0011, 0012, and 0018; timeout follows ADR 0021. New choices are recorded in ADRs 0022 and 0023.

## Research references

- https://flask-appbuilder.readthedocs.io/en/latest/rest_api.html
- https://github.com/dpgaspar/Flask-AppBuilder/blob/v4.5.3/flask_appbuilder/api/__init__.py
- https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/models/sqla/filters.py
- https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/manager.py
- https://github.com/apache/superset/blob/6.1.0/superset/security/manager.py
- https://github.com/apache/superset/blob/6.1.0/superset/charts/api.py
- https://github.com/apache/superset/blob/6.1.0/superset/views/log/api.py

## Decision follow-up

Decision record update required: completed in [ADR 0022](../decisions/0022-explicit-list-query-controls.md) and [ADR 0023](../decisions/0023-environment-bound-api-keys.md). ADR 0012 remains unchanged: optional query selection was not justified. Corrected the older API-key design to remove its abstract-inheritance assumption.
