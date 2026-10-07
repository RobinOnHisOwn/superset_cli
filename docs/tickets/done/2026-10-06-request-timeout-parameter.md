# Add per-invocation HTTP timeout parameter

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: [plan](../../plans/2026-10-06-http-timeout.md), [ADR 0021](../../decisions/0021-per-invocation-http-timeout.md), `tests/test_timeout.py`

## Context

Slow query workflows need longer HTTP timeouts without recreating authentication or CSRF handling. A longer timeout does not fix HTTP 400 errors.

## Definition of done

- [x] Root `--timeout SECONDS` before the command covers API, chart data, SQL Lab, and authentication clients.
- [x] Validate finite positive values before browser/network access; preserve the 30-second default.
- [x] Verify timeout metadata on authentication, JWT refresh/recovery, CSRF, and query requests.
- [x] Document HTTPX phase/inactivity semantics, not a total runtime deadline.
- [x] Preserve write guards and bounded auth recovery; never automatically retry sent mutations. Report timeout outcomes as unknown.
- [x] Test defaults, custom values, invocation isolation, invalid values, and timeout errors with mocked HTTP.
- [x] Write a plan, CLI help, README examples, and durable policy record.

## Verification

Completed 2026-10-06 on `fix/open-todos-chart-docs`, based on freshly fetched `refs/remotes/origin/main`.

- Initial timeout tests: 11 failures because `--timeout` was absent.
- Focused timeout/API/JWT/client tests: 100 passed (13 timeout cases).
- `uv run pytest -v`: 850 passed, 13 skipped.
- `uv run superset-cli --help`: root option and default displayed.
- `uv build`: wheel and source distribution built.
- Manual root-option smoke: custom timeout with `instances list` exited 0; `--timeout nan api prod /api/v1/me/` exited 2 before access.
- `git diff --check`: clean.

All project commands ran through `direnv exec` in the worktree. No live Superset verification or writes were performed.
