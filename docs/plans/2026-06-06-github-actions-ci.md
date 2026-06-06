# GitHub Actions CI Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Add a GitHub Actions CI workflow that validates this Python CLI project on pull requests and pushes to `main` using `uv`.

**Architecture:** Add a single repository workflow file at `.github/workflows/ci.yml` that runs on GitHub-hosted Ubuntu runners with a Python version matrix for `3.12` and `3.13`. Keep the workflow small and aligned with the repository's local verification commands: install with `uv`, run tests, smoke-check the CLI, build distributions, and smoke-test the built wheel.

**Tech Stack:** GitHub Actions, `uv`, Python, `pytest`, YAML

---

### Task 1: Add a failing repository-file test for the CI workflow

**Files:**
- Modify: `tests/test_repo_files.py`

**Step 1: Write the failing test**

Add a test that asserts `.github/workflows/ci.yml` exists and contains the expected CI contract:
- triggers on `pull_request`
- triggers on pushes to `main`
- uses a Python matrix with `3.12` and `3.13`
- runs `uv sync --locked --group dev`
- runs `uv run pytest -v`
- runs `uv run superset-cli --help`
- runs `uv build`
- runs a wheel smoke test with `uv run --isolated --no-project --with dist/*.whl superset-cli --help`

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_repo_files.py -v`
Expected: FAIL because `.github/workflows/ci.yml` does not exist yet.

### Task 2: Add the CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Write minimal implementation**

Create a GitHub Actions workflow that:
- runs on `pull_request`
- runs on push to `main`
- uses workflow-level concurrency with `cancel-in-progress: true`
- sets minimal `contents: read` permissions
- runs a single `test` job on `ubuntu-latest`
- uses a Python matrix for `3.12` and `3.13`
- checks out the repo
- sets up Python
- sets up `uv` with cache enabled
- runs the repository verification commands and wheel smoke test

Use pinned action SHAs and annotate them with the corresponding release tags in comments.

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_repo_files.py -v`
Expected: PASS.

### Task 3: Verify the workflow file and repository health

**Files:**
- Verify only

**Step 1: Validate the workflow YAML parses**

Run: `uv run python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())"`
Expected: PASS with no output.

**Step 2: Run the focused test suite**

Run: `uv run pytest tests/test_repo_files.py -v`
Expected: PASS.

**Step 3: Run broader repository verification**

Run:
- `uv run pytest -v`
- `uv run superset-cli --help`
- `uv build`

Expected: PASS.

## Decision follow-up

No durable decision change.
