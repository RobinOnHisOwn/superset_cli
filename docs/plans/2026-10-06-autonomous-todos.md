# Autonomous todo implementation

**Date:** 2026-10-06

## Goal

Implement the verified todo queue incrementally without live mutations or speculative API contracts.

## Planned changes

1. Inspect each ticket, relevant decisions, code, and tests; retain unresolved prerequisites as explicit blockers.
2. Implement chart-data failure exits and CSV output first, using failing CLI tests before code. Preserve raw JSON, accept legacy responses lacking status, and reject only entirely failed or empty results. Do not infer measure columns or reject legitimate NULL values.
3. CSV uses a blank line between query tables, `colnames` headers, and UTC conversion only for numeric `__timestamp` values. Reject simultaneous `--csv` and `--json`.
4. Add role/user/RLS list/get reads through existing `_run_list`/`_run_get` helpers, plus saved-chart Explore reads. Use verified plural FAB endpoints rather than the stale singular paths in the tickets. Explore form-data unwraps `form_data`, not `result`.
5. Export dashboard/chart/dataset/database ZIPs using binary GET, integer-list Rison, ZIP validation before opening output, and exclusive creation unless `--force` is supplied.
6. Add stdlib-only inline Markdown relative-link validation to pytest.
7. Apply chart-data overrides to a deep copy of the saved query context: update every query's time range and append string equality filters without changing saved chart state. Keep the original GET path when no overrides are present. Refuse absent/invalid contexts.
8. Improve generic HTTP failure diagnostics on stderr with method/path/status and bounded selected server details, redacting request secrets and suppressing HTML tracebacks. Preserve existing auth/not-found handling and never retry mutations.
9. Continue other tickets only after their API and safety prerequisites are verified. Keep each contract change covered by focused tests and documentation.

## Verified prerequisites

- Main checkout is human-owned; changes use `fix/autonomous-todos` from fetched `refs/remotes/origin/main`.
- `origin/main` is ambiguous because a local branch has that name; the qualified remote reference resolves correctly.
- Six newer ticket documents exist only in the human checkout; their ticket-only diff is copied into the worktree without merging branches.
- Baseline chart-data tests: 5 passed.
- Superset publishes a chart-data response schema and query-object schema; no live API calls are required for output handling.

## Verification

- Confirm new focused tests fail before implementation, then pass.
- Run `uv run pytest -v`, CLI help/smoke checks, and `uv build` through `direnv exec`.
- Validate changed plan and decision documents.
- Run commands from the worktree directory as well as through `direnv exec`; direnv changes the environment, not the working directory.

## Results and remaining work

Completed ten tickets: chart-data CSV, failure exits, and overrides; role/user/RLS reads; Explore reads; binary exports; relative documentation links; actionable HTTP errors. Completion evidence is recorded in `docs/tickets/done/`.

Changed application files: `src/superset_cli/cli.py` and `src/superset_cli/client.py`. Tests: updated chart-data/dashboard-error tests and added override, security/Explore, export, docs-link, and API-error test files. Updated README, architecture/decision indexes, ticket states, and ADRs 0012–0016. Resolved committed conflict markers in two imported ticket documents and removed their non-example hostnames.

Verification from the worktree through `direnv exec`:

- `uv run pytest -v`: **579 passed**.
- `uv run superset-cli --help` and `uv run superset-cli charts data --help`: exit 0.
- `uv build`: built source distribution and wheel.
- `uv run python /tmp/superset-todos-smoke.py`: real subprocess CSV success and empty-result JSON failure passed against a synthetic local HTTP server.
- `uv run pytest tests/test_docs_links.py -q` after ticket moves: **2 passed**.
- `git diff --check`: clean.
- `specdocs_validate`: reports an existing `docs/architecture/README.md` filename-pattern error; a clean specdocs result is not claimed.

Consulted ADRs 0001, 0010, and 0011 (custom API authentication), plus the relevant security, Explore, export, JWT/API-key, and docs-verification design plans.

Nine todos remain **not implemented**: API-key auth, default instance selection, JWT auth, Firefox/Zen session-cookie recovery, dashboard rendering recipe, API/companion-skill handoff, Playwright-compatible state, companion-skill refresh, and release capability preflight. API-key support retains its explicit target-release/live-auth prerequisites. The other remaining items are pending work, not reported as completed or artificially blocked.

No live Superset or browser checks were performed. Companion-skill sources and installed release capabilities were not changed or verified. Exports use memory buffers and `--force` is not transactional. No commit, push, publication, or merge was performed. Skill evolution is deferred: the management tool does not expose an authoritative-source path, and this setup forbids editing deployed skills. Reusable findings (qualified Git refs and explicit worktree cwd) are recorded in this plan pending a source-repository skill update.

## Decision follow-up

Decision record update required: `docs/decisions/0012-chart-data-output-contract.md`, `docs/decisions/0013-security-read-scope.md`, `docs/decisions/0014-binary-asset-exports.md`, `docs/decisions/0015-chart-query-overrides.md`, and `docs/decisions/0016-api-failure-diagnostics.md`.
