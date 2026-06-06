# Direnv Auto-Activation for Devenv Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Make this repository auto-activate its existing `devenv` environment through `direnv` when entering the project directory.

**Architecture:** Keep the current `devenv.nix` as the source of truth for the development environment and add a repo-committed `.envrc` that delegates activation to `devenv` using the current documented integration. Add a small repository-file test so the auto-activation contract is exercised through TDD, then update the human quickstart docs with the required `direnv allow` step.

**Tech Stack:** `devenv`, `direnv`, Python `pytest`, Markdown

---

### Task 1: Add a failing repository-file test for direnv activation

**Files:**
- Create: `tests/test_repo_files.py`

**Step 1: Write the failing test**

Add a test that asserts the repository contains a `.envrc` file with the current `devenv`-recommended activation lines.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_repo_files.py -v`
Expected: FAIL because `.envrc` does not exist yet.

### Task 2: Add the direnv activation file and document it

**Files:**
- Create: `.envrc`
- Modify: `README.md`

**Step 1: Write minimal implementation**

Create `.envrc` with the documented `devenv direnvrc` bootstrap and `use devenv` call. Update `README.md` quickstart to show `direnv allow` before running project commands and mention that entering the directory will auto-load the environment.

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_repo_files.py -v`
Expected: PASS.

### Task 3: Verify real direnv activation and broader repo health

**Files:**
- Verify only

**Step 1: Verify the shell file is syntactically valid**

Run: `bash -n .envrc`
Expected: PASS with no output.

**Step 2: Verify direnv can load the repo environment**

Run: `direnv allow && direnv exec . bash -lc 'python --version && uv --version && command -v python && command -v uv'`
Expected: PASS with Python and `uv` available from the activated environment.

**Step 3: Run repository verification**

Run:
- `uv run pytest -v`
- `uv run superset-agent --help`
- `uv build`

Expected: PASS.

## Decision follow-up

No durable decision change.
