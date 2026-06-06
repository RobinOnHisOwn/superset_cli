# List Filtering and Ordering Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Add a small shared search and ordering contract to existing read-only list commands without changing current JSON payload shapes.

**Architecture:** Keep the existing Typer command structure and extend the shared list-query builder in `client.py`. Expose a single `--search` flag that maps to each resource's primary display column plus pass-through `--order-column` and `--order-direction` flags, then forward them as Superset `q` params.

**Tech Stack:** Python, Typer, httpx, pytest, uv

---

### Task 1: Add failing CLI tests for shared list-query flags

**Files:**
- Modify: `tests/test_dashboards.py`
- Modify: `tests/test_charts.py`
- Modify: `tests/test_datasets.py`
- Modify: `tests/test_databases.py`

**Step 1: Write the failing test**

Add tests that:
- invoke each `list` command with `--search`, `--order-column`, and `--order-direction`
- assert the CLI accepts the new flags
- assert each command forwards `search`, `order_column`, and `order_direction` to `FakeSupersetClient`
- assert `--json` output shape is unchanged when the new flags are used

**Step 2: Run test to verify it fails**

Run:
- `uv run pytest tests/test_dashboards.py tests/test_charts.py tests/test_datasets.py tests/test_databases.py -v`

Expected: FAIL because the CLI commands and fake client do not accept the new keyword arguments yet.

### Task 2: Add failing client tests for Superset `q` payload building

**Files:**
- Modify: `tests/test_client.py`

**Step 1: Write the failing test**

Add tests that:
- verify `build_list_params()` includes `filters`, `order_column`, and `order_direction` when provided
- verify `list_dashboards`, `list_charts`, `list_datasets`, and `list_databases` send the combined `q` payload through `_get()`
- verify the search filter uses `{"col": <resource search column>, "opr": "ct", "value": <search text>}`

**Step 2: Run test to verify it fails**

Run:
- `uv run pytest tests/test_client.py -v`

Expected: FAIL because the builder and list methods only support `page` and `page_size`.

### Task 3: Implement the minimal shared query support

**Files:**
- Modify: `src/superset_cli/client.py`
- Modify: `src/superset_cli/cli.py`
- Modify: `tests/fakes.py`

**Step 1: Write minimal implementation**

Implement:
- optional `search`, `search_column`, `order_column`, and `order_direction` support in `build_list_params()`
- list methods that accept the new optional args and map `--search` to:
  - dashboards → `dashboard_title`
  - charts → `slice_name`
  - datasets → `table_name`
  - databases → `database_name`
- CLI flags `--search`, `--order-column`, and `--order-direction` on all four list commands
- fake client signatures updated to match the new interface

**Step 2: Run tests to verify they pass**

Run:
- `uv run pytest tests/test_client.py tests/test_dashboards.py tests/test_charts.py tests/test_datasets.py tests/test_databases.py -v`

Expected: PASS.

### Task 4: Update user-facing docs

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Step 1: Document the new flags**

Update:
- README command examples for list commands using `--search` and ordering flags
- architecture doc scope/module/command sections to mention the new shared list-query controls

**Step 2: Run focused smoke checks**

Run:
- `uv run superset-cli dashboards list --help`
- `uv run superset-cli charts list --help`

Expected: help output shows the new flags.

### Task 5: Run repository verification

**Files:**
- Modify if needed: `docs/tickets/in-progress/2026-06-06-list-filtering-and-ordering.md`

**Step 1: Run the verification commands**

Run:
- `uv run pytest -v`
- `uv run superset-cli --help`
- `uv build`

Expected: PASS.

**Step 2: Finish the ticket**

Move the ticket to `docs/tickets/done/` and set `Status: done` after verification passes.

## Decision follow-up

No durable decision change.
