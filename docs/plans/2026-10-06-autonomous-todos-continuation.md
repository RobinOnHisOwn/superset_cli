# Autonomous todo continuation

**Date:** 2026-10-06

## Goal

Continue the remaining nine tickets with verified prerequisites, failing tests, and no live mutations or publication.

## Planned changes

1. Add an explicit Playwright-compatible auth export, leaving existing expiry values and consumers unchanged while preserving available cookie attributes. Inspect loader expiry units; normalize legacy millisecond inputs only in the export, reject invalid values, preserve attributes, and smoke-test a synthetic context with optional Playwright.
2. Clarify missing persisted-cookie diagnostics for Firefox/Zen and document supported-browser recovery; do not claim detection of browser-memory sessions.
3. Add direct JWT login/refresh/logout and per-instance auth selection with environment-only credentials, private token storage, and one refresh retry for GET only. Never retry sent writes.
4. Resolve optional instance positional parsing before implementing default-instance precedence. Use native Click/Typer parsing where possible; preserve old command invocations and fail safely on ambiguity.
5. Inspect published artifacts and authoritative companion-skill repositories before changing releases, recipes, or browser helpers. Verify all recipe behavior with mocks/controlled browser content.
6. Keep API-key auth gated on confirmed target-release and live-read prerequisites rather than inventing support.

## Assumptions

- Verified: existing worktree contains the prior ten completed tickets; main checkout remains unchanged.
- Verified: an installed Chrome executable is available for a synthetic optional Playwright smoke check.
- Proposed: explicit export is safer than silently rewriting existing auth state.
- Verified: authoritative companion skill located and updated in a separate isolated `claude-skills` worktree; no deployed skill edits.
- Unknown: target deployment API-key capability and authoritative legacy-workaround source; these remain gated.

## Verification

- New failing focused tests before production changes.
- Focused auth/config/CLI tests followed by the full suite, CLI smoke checks, and build.
- Controlled synthetic browser checks only; do not inspect actual browser cookies or launch interactive login.
- Validate plans and decision documents and record any pre-existing validator failures.

## Completion report

### Outcome

Seven further tickets moved to `done`: default instance selection, JWT, unavailable Firefox/Zen-cookie diagnostics, explicit Playwright export, browser rendering recipe, authenticated API documentation, and release/capability preflight. Together with the previous ten, **17 of the original 19 tickets are complete**.

Two remain: API-key auth is gated on verified target-release/deployment support and contract; companion recipes are partially implemented in their authoritative source, but the legacy workaround source/rollout remains unresolved. No deployed skill edit, duplicate skill catalog, real browser-cookie inspection, interactive login, live Superset mutation, commit, push, merge, or publication was performed.

### Files changed

- `src/superset_cli/{auth,cli,client,config,models}.py`; new `jwt_auth.py` and `instance_selection.py`.
- `scripts/verify_dashboard.py`; new focused tests for defaults, JWT, export, recovery, rendering, and version.
- `pyproject.toml` and `uv.lock`: distinct unpublished 0.2.0 build, no new runtime dependency.
- README, architecture, glossary, ADR 0008, ADRs 0017–0019, decision index, this plan, and ticket lifecycle/evidence.
- External authoritative companion `skills/datateam/superset-cli/SKILL.md`, isolated `claude-skills` branch `docs/superset-cli-capability-recipes`; integration is left to the human. Reusable provenance/upgrade/auth/render guidance is saved there. `skill_manage` only targets deployed agent skills and could not locate this companion; no duplicate deployed copy was created.

### Verification evidence

All project commands ran from the isolated Superset worktree; `direnv exec` does not change cwd.

- `direnv exec "$PWD" uv run pytest -v`: **643 passed, 13 optional-browser skips**, after the final code change.
- `direnv exec "$PWD" uv run --with playwright pytest tests/test_dashboard_recipe.py tests/test_playwright_export.py -q`: **27 passed**, including all optional-browser cases and actual CLI tab/container-screenshot checks.
- Final combined `direnv exec "$PWD" uv run --with playwright pytest -v`, after code and ticket/doc changes: **656 passed**, no skips or failures.
- Ticket status/folder consistency, final plan section, and all 14 README Bash example blocks verified (`bash -n`); help/JWT-help/version smoke checks passed again.
- `uv build`: wheel and sdist 0.2.0 built successfully; source `--help` and eager `--version` smoke checks passed.
- Isolated official 0.1.0 wheel installation → final local 0.2.0 wheel upgrade, followed by copied focused tests from outside the repository: **90 passed**. Imported package path was asserted to be the isolated wheel, not editable source; running `--version` reported 0.2.0.
- Latest PyPI rechecked as 0.1.0; official wheel SHA-256 matched PyPI. Both synthetic config/auth byte digests remained unchanged after upgrade. Same-version local installation and official wheel differed in capabilities, so `uvx --from` tool reuse is not authoritative artifact evidence.
- `git diff --check` clean; relative-doc-link test is included in the full suite. Specdocs validation still reports its pre-existing `docs/architecture/README.md` plan-filename classification error, not a clean validation result.

### Consulted reasoning and limits

Consulted ADR 0008, both existing ADR 0011 records (custom API authentication and publishing), and the original JWT/default-instance designs. Superset 6.1.0 source disproved the older JWT/no-CSRF claim: ordinary modifying APIs remain CSRF-protected. JWT token syntax/transport guards follow RFC 6750; expiry is display-only. Browser tests use controlled Chrome, not live deployment acceptance; text/SVG/2D-canvas evidence cannot prove query semantics, color contrast, or occlusion without separate inspection. No live JWT/API-key auth or user-tool upgrade was exercised.

## Decision follow-up

Decision record update required: implemented in `docs/decisions/0017-explicit-playwright-auth-export.md`, `docs/decisions/0018-per-instance-jwt-auth.md`, `docs/decisions/0019-default-instance-selection.md`, and ADR 0008's evidence-based browser recovery correction. Release provenance follows existing ADR 0011; no publication was performed.
