# OpenAPI Spec Fetch Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Add a read-only CLI command that fetches the live Superset OpenAPI specification for a configured instance.

**Architecture:** Add a small `SupersetClient` wrapper for `/api/v1/_openapi`, then expose a focused top-level `openapi fetch` command that reuses existing instance resolution, auth-state guards, and API error handling. Preserve the raw schema in `--json` mode and keep human output to a concise summary.

**Tech Stack:** Python, Typer, httpx, pytest, uv

---

### Task 1: Add failing tests for the new command

**Files:**
- Create: `tests/test_openapi.py`
- Modify: `tests/fakes.py`

**Step 1: Write the failing tests**

Add tests for:
- `openapi fetch <instance> --json`
- human-readable output showing a few top-level schema fields
- unknown-instance and missing-auth guards
- network and auth/not-found error handling
- client closure

**Step 2: Run test to verify it fails**

Run:
- `uv run pytest tests/test_openapi.py -v`

Expected: FAIL because the command and fake client method do not exist yet.

### Task 2: Add failing client test and minimal implementation

**Files:**
- Modify: `tests/test_client.py`
- Modify: `src/superset_cli/client.py`

**Step 1: Write the failing test**

Add a unit test verifying `get_openapi_spec()` returns the raw JSON payload from `/api/v1/_openapi` without reshaping it.

**Step 2: Run test to verify it fails**

Run:
- `uv run pytest tests/test_client.py -v`

Expected: FAIL because the method does not exist yet.

**Step 3: Write minimal implementation**

Add `SupersetClient.get_openapi_spec()` using the documented `/api/v1/_openapi` endpoint.

### Task 3: Add minimal CLI support

**Files:**
- Modify: `src/superset_cli/cli.py`

**Step 1: Write minimal implementation**

Add a top-level `openapi` command group with `fetch` subcommand that:
- requires a known instance
- requires saved auth state
- reuses `_api_errors()`
- emits the raw schema in `--json` mode
- prints a concise human-readable summary otherwise

**Step 2: Run targeted tests**

Run:
- `uv run pytest tests/test_openapi.py tests/test_client.py -v`

Expected: PASS.

### Task 4: Update docs

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Step 1: Document the new command**

Update command examples, scope notes if needed, command maps, and test maps.

### Task 5: Verify and close the ticket

**Files:**
- Modify: `docs/tickets/in-progress/2026-06-06-openapi-spec-fetch.md`

**Step 1: Run verification**

Run:
- `uv run pytest -v`
- `uv run superset-cli openapi --help`
- `uv run superset-cli --help`
- `uv build`

Expected: PASS.

**Step 2: Finish the ticket**

Move the ticket to `docs/tickets/done/` and set `Status: done` after verification passes.

## Decision follow-up

No durable decision change.
