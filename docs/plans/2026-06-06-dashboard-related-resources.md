# Dashboard Related-Resources Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Add read-only dashboard subcommands that fetch the charts and datasets related to a dashboard.

**Architecture:** Extend `SupersetClient` with two small wrapper methods for the existing Superset dashboard relationship endpoints, then expose matching `dashboards` subcommands that reuse existing auth guards, API error handling, and human/JSON output patterns.

**Tech Stack:** Python, Typer, httpx, pytest, uv

---

### Task 1: Add failing command tests for dashboard charts and datasets

**Files:**
- Modify: `tests/test_dashboards_get.py`
- Modify: `tests/fakes.py`

**Step 1: Write the failing tests**

Add tests for:
- `dashboards charts <instance> <id_or_slug> --json`
- `dashboards datasets <instance> <id_or_slug> --json`
- human-readable output for both commands
- unknown-instance and missing-auth guards for both commands
- 404 and network error handling for at least one command per endpoint type
- client closure for the new commands

**Step 2: Run test to verify it fails**

Run:
- `uv run pytest tests/test_dashboards_get.py -v`

Expected: FAIL because the commands and fake client methods do not exist yet.

### Task 2: Add minimal client support

**Files:**
- Modify: `src/superset_cli/client.py`
- Modify: `tests/test_client.py`

**Step 1: Write the failing test**

Add unit tests that verify:
- `get_dashboard_charts(id_or_slug)` unwraps `{"result": [...]}`
- `get_dashboard_datasets(id_or_slug)` unwraps `{"result": [...]}`

**Step 2: Run test to verify it fails**

Run:
- `uv run pytest tests/test_client.py -v`

Expected: FAIL because the methods do not exist yet.

**Step 3: Write minimal implementation**

Add `SupersetClient` methods for:
- `/api/v1/dashboard/{id_or_slug}/charts`
- `/api/v1/dashboard/{id_or_slug}/datasets`

### Task 3: Add minimal CLI support

**Files:**
- Modify: `src/superset_cli/cli.py`

**Step 1: Write minimal implementation**

Add `dashboards charts` and `dashboards datasets` commands that:
- require a known instance
- require saved auth state
- reuse `_api_errors()`
- emit raw arrays in `--json` mode
- print concise line-oriented human output in non-JSON mode

**Step 2: Run targeted tests**

Run:
- `uv run pytest tests/test_dashboards_get.py tests/test_client.py -v`

Expected: PASS.

### Task 4: Update docs

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Step 1: Document the new commands**

Update current command examples and the architecture command map/module notes for the new dashboard-related reads.

### Task 5: Verify and close the ticket

**Files:**
- Modify: `docs/tickets/in-progress/2026-06-06-dashboard-related-resources.md`

**Step 1: Run verification**

Run:
- `uv run pytest -v`
- `uv run superset-cli dashboards --help`
- `uv run superset-cli --help`
- `uv build`

Expected: PASS.

**Step 2: Finish the ticket**

Move the ticket to `docs/tickets/done/` and set `Status: done` after verification passes.

## Decision follow-up

No durable decision change.
