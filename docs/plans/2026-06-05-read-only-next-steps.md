# Read-only Next Steps Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Extend the current read-only Superset CLI from bootstrap-complete MVP to a more complete and resilient day-to-day tool.

**Architecture:** Keep the existing Typer + helper-module split. Add missing read-only resource detail commands, strengthen shared API error handling, extend list-query ergonomics without changing existing JSON output contracts, and fill test coverage gaps before any behavioral change.

**Tech Stack:** Python, Typer, httpx, Playwright, pytest, uv

---

### Task 1: Add detail commands for charts, datasets, and databases

**Files:**
- Modify: `src/superset_agent_cli/client.py`
- Modify: `src/superset_agent_cli/cli.py`
- Create: `tests/test_charts_get.py`
- Create: `tests/test_datasets_get.py`
- Create: `tests/test_databases_get.py`
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Step 1: Write the failing tests**

Add tests for:
- `charts get <instance> <id_or_uuid> --json`
- `datasets get <instance> <id_or_uuid> --json`
- `databases get <instance> <id> --json`
- missing auth-state guard behavior for each command

**Step 2: Run tests to verify they fail**

Run:
- `uv run pytest tests/test_charts_get.py -v`
- `uv run pytest tests/test_datasets_get.py -v`
- `uv run pytest tests/test_databases_get.py -v`

Expected: FAIL because the commands and client methods do not exist yet.

**Step 3: Write minimal implementation**

Add matching `SupersetClient` methods for:
- `/api/v1/chart/{id_or_uuid}`
- `/api/v1/dataset/{id_or_uuid}`
- `/api/v1/database/{pk}`

Add Typer `get` commands following the existing `dashboards get` pattern.

**Step 4: Run tests to verify they pass**

Run:
- `uv run pytest tests/test_charts_get.py -v`
- `uv run pytest tests/test_datasets_get.py -v`
- `uv run pytest tests/test_databases_get.py -v`

Expected: PASS.

### Task 2: Add user-friendly API error handling for auth expiry, 404s, and network failures

**Files:**
- Modify: `src/superset_agent_cli/client.py`
- Modify: `src/superset_agent_cli/cli.py`
- Create or modify: `tests/test_auth_validate.py`
- Modify: `tests/test_dashboards.py`
- Modify: `tests/test_dashboards_get.py`
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Step 1: Write the failing tests**

Add command-level tests that simulate:
- expired/invalid auth state causing 401 or redirect-style auth failure
- missing resource causing 404 on `dashboards get`
- network failure from `httpx`

Assert clear stderr/stdout messaging and exit code `1`, not raw tracebacks.

**Step 2: Run tests to verify they fail**

Run targeted pytest commands for the updated tests.

Expected: FAIL because current code calls `raise_for_status()` without CLI handling.

**Step 3: Write minimal implementation**

Add a small shared error-handling path so CLI commands convert common `httpx` failures into concise user-facing messages.

**Step 4: Run tests to verify they pass**

Run the targeted pytest commands.

Expected: PASS.

### Task 3: Add pagination and list-query controls without changing existing JSON payload shape

**Files:**
- Modify: `src/superset_agent_cli/client.py`
- Modify: `src/superset_agent_cli/cli.py`
- Modify: `tests/test_dashboards.py`
- Modify: `tests/test_charts.py`
- Modify: `tests/test_datasets.py`
- Modify: `tests/test_databases.py`
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Step 1: Write the failing tests**

Add tests for optional list flags such as:
- `--page`
- `--page-size`

Verify the CLI forwards query arguments to the right REST endpoints while preserving the current response body shape in `--json` mode.

**Step 2: Run tests to verify they fail**

Run the targeted list-command pytest files.

Expected: FAIL because list methods currently hardcode bare endpoint paths.

**Step 3: Write minimal implementation**

Extend shared list methods to accept optional query params and pass them through to Superset list endpoints.

**Step 4: Run tests to verify they pass**

Run the targeted pytest files.

Expected: PASS.

### Task 4: Complete local-state lifecycle commands

**Files:**
- Modify: `src/superset_agent_cli/config.py`
- Modify: `src/superset_agent_cli/auth.py`
- Modify: `src/superset_agent_cli/cli.py`
- Create: `tests/test_instances_remove.py`
- Create: `tests/test_auth_logout.py`
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Step 1: Write the failing tests**

Add tests for:
- `instances remove <name>` removing an instance from config
- `auth logout <instance>` removing saved local auth artifacts for one instance
- clear error messages when the instance does not exist or auth state is already absent

**Step 2: Run tests to verify they fail**

Run:
- `uv run pytest tests/test_instances_remove.py -v`
- `uv run pytest tests/test_auth_logout.py -v`

Expected: FAIL because the commands do not exist yet.

**Step 3: Write minimal implementation**

Implement local-only removal behavior. Do not add any write-capable Superset API operations.

**Step 4: Run tests to verify they pass**

Run the targeted pytest commands.

Expected: PASS.

### Task 5: Close test coverage gaps for existing human-readable output and guard paths

**Files:**
- Modify: `tests/test_auth_status.py`
- Modify: `tests/test_auth_validate.py`
- Modify: `tests/test_dashboards.py`
- Modify: `tests/test_dashboards_get.py`
- Modify: `tests/test_charts.py`
- Modify: `tests/test_datasets.py`
- Modify: `tests/test_databases.py`
- Modify: `tests/test_cli.py`

**Step 1: Write the failing tests**

Add tests for:
- human-readable output paths, not only `--json`
- unknown-instance behavior for all command groups using `_require_instance`
- empty-result human output for each list command

**Step 2: Run tests to verify they fail**

Run the updated targeted tests.

Expected: FAIL where current behavior is untested or inconsistent.

**Step 3: Write minimal implementation**

Only change implementation where tests reveal an actual gap or inconsistency.

**Step 4: Run tests to verify they pass**

Run the updated targeted tests.

Expected: PASS.

### Task 6: Run full verification and optional live read-only smoke validation

**Files:**
- Modify if needed: `README.md`
- Modify if needed: `docs/architecture/README.md`
- Modify if needed: `docs/decisions/0001-read-only-bootstrap-scope.md`
- Modify if needed: `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`

**Step 1: Run the full automated suite**

Run:
- `uv run pytest -v`
- `uv run superset-agent --help`
- `uv build`

Expected: PASS.

**Step 2: Run manual CLI smoke checks**

Run representative commands for new and changed paths using temporary config/state locations.

Expected: clear output in both human and `--json` modes.

**Step 3: Optionally run live read-only validation**

If a real Superset instance is available and explicitly approved, run minimal read-only checks for login, auth validation, and at least one resource list/detail command.

**Step 4: Promote durable decisions if needed**

Only update a decision record if the work changes product scope, auth model, or long-term CLI contract.

## Decision follow-up

No durable decision change.
