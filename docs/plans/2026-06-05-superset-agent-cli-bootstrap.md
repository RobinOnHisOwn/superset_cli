# Superset Agent CLI Bootstrap Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Bootstrap a Python-based Superset agent CLI project with uv-managed dependencies and devenv Python support, starting with read-only operations.

**Architecture:** Use a minimal `src/` Python package with a Typer entrypoint, small config/auth/client modules, and pytest coverage for basic CLI behavior. Configure devenv to provide Python + uv + automatic `uv sync` so the repo is reproducible for local development.

**Tech Stack:** Python, uv, Typer, httpx, pytest, devenv

---

### Task 1: Configure project metadata and devenv

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Modify: `devenv.nix`

**Step 1: Write the failing test**

Create a simple verification command expectation in `tests/test_cli.py` that assumes a CLI package exists and that `--help` works.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL because the project/package does not exist yet.

**Step 3: Write minimal implementation**

Add `pyproject.toml` with uv-managed dependencies and a console script. Update `devenv.nix` to enable Python, venv, uv, and automatic sync.

**Step 4: Run test to verify it passes**

Run: `devenv test` and `uv run pytest tests/test_cli.py -v`
Expected: pytest can resolve the project environment.

### Task 2: Add minimal read-only CLI skeleton

**Files:**
- Create: `src/superset_agent_cli/__init__.py`
- Create: `src/superset_agent_cli/cli.py`
- Create: `src/superset_agent_cli/main.py`
- Create: `src/superset_agent_cli/config.py`
- Create: `src/superset_agent_cli/models.py`

**Step 1: Write the failing test**

Add tests for `--help` and a read-only command like `instances list`.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL because command modules do not exist yet.

**Step 3: Write minimal implementation**

Implement a Typer app with a top-level help message and an `instances list` command that returns an empty result set in human or JSON mode.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS.

### Task 3: Add config loading tests and implementation

**Files:**
- Create: `tests/test_config.py`
- Modify: `src/superset_agent_cli/config.py`

**Step 1: Write the failing test**

Test default config path resolution and empty-instance behavior.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL because config loading is incomplete.

**Step 3: Write minimal implementation**

Implement config models and a loader for a local YAML config file path.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS.

### Task 4: Verify bootstrap

**Files:**
- Test: `tests/test_cli.py`
- Test: `tests/test_config.py`

**Step 1: Run the focused test suite**

Run: `uv run pytest -v`
Expected: PASS.

**Step 2: Run devenv verification**

Run: `devenv test`
Expected: PASS with Python/uv environment available.

**Step 3: Manual smoke check**

Run: `uv run superset-agent --help`
Expected: help output for the CLI.

## Decision follow-up

Decision record update required:
- `docs/decisions/0001-read-only-bootstrap-scope.md`
- `docs/decisions/0002-local-config-and-auth-state-storage.md`
- `docs/decisions/0003-browser-login-with-playwright-and-saved-storage-state.md`
