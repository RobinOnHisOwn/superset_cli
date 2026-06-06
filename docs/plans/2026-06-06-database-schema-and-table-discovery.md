# Database Schema and Table Discovery Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Add read-only database subcommands that list accessible schemas and tables for a configured Superset database.

**Architecture:** Extend `SupersetClient` with small wrappers around Superset's database schema and table discovery endpoints. Expose matching `databases` subcommands that reuse existing auth guards, API error handling, and human/JSON output conventions while forwarding the documented `q` params.

**Tech Stack:** Python, Typer, httpx, pytest, uv

---

### Task 1: Add failing CLI tests for schema and table discovery

**Files:**
- Modify: `tests/test_databases_get.py`
- Modify: `tests/fakes.py`

**Step 1: Write the failing tests**

Add tests for:
- `databases schemas <instance> <pk> --json`
- `databases tables <instance> <pk> --schema analytics --json`
- human-readable output for both commands
- unknown-instance and missing-auth guards
- 404 and network error handling
- client closure
- parameter forwarding for `--catalog`, `--force`, and required `--schema`

**Step 2: Run test to verify it fails**

Run:
- `uv run pytest tests/test_databases_get.py -v`

Expected: FAIL because the commands and fake client methods do not exist yet.

### Task 2: Add failing client tests for discovery endpoints

**Files:**
- Modify: `tests/test_client.py`
- Modify: `src/superset_cli/client.py`

**Step 1: Write the failing tests**

Add unit tests that verify:
- `get_database_schemas(pk, catalog, force)` unwraps `{"result": [...]}` and forwards the documented query payload
- `get_database_tables(pk, schema_name, catalog_name, force)` returns the full table envelope and forwards the documented query payload

**Step 2: Run test to verify it fails**

Run:
- `uv run pytest tests/test_client.py -v`

Expected: FAIL because the methods do not exist yet.

**Step 3: Write minimal implementation**

Add wrappers for:
- `/api/v1/database/{pk}/schemas/` with `q={catalog, force}`
- `/api/v1/database/{pk}/tables/` with `q={schema_name, catalog_name, force}`

### Task 3: Add minimal CLI support

**Files:**
- Modify: `src/superset_cli/cli.py`

**Step 1: Write minimal implementation**

Add `databases schemas` and `databases tables` commands that:
- require a known instance
- require saved auth state
- reuse `_api_errors()`
- emit raw server payloads in `--json` mode
- print concise line-oriented human output otherwise

### Task 4: Update docs

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Step 1: Document the new commands**

Update command examples and architecture command maps / test maps.

### Task 5: Verify and close the ticket

**Files:**
- Modify: `docs/tickets/in-progress/2026-06-06-database-schema-and-table-discovery.md`

**Step 1: Run verification**

Run:
- `uv run pytest -v`
- `uv run superset-cli databases --help`
- `uv run superset-cli --help`
- `uv build`

Expected: PASS.

**Step 2: Finish the ticket**

Move the ticket to `docs/tickets/done/` and set `Status: done` after verification passes.

## Decision follow-up

No durable decision change.
