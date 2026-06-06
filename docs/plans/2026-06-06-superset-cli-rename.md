# Superset CLI Rename Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Rename the product from `superset-cli` / `superset-cli` to `superset-cli` / `superset-cli` across code, packaging, default local paths, tests, and current repository documentation.

**Architecture:** Keep behavior and read-only scope unchanged while performing a focused identity rename. Rename the Python package from `superset_cli` to `superset_cli`, update the console script entrypoint and default local storage paths to the new product name, then refresh current docs and CI checks to match.

**Tech Stack:** Python, `uv`, `pytest`, Typer, Hatchling, YAML, Markdown

---

### Task 1: Add failing tests for the renamed public and local surfaces

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_repo_files.py`

**Step 1: Write the failing tests**

Update tests to assert:
- help output says `Superset CLI` instead of `Superset CLI`
- default config and state paths use `superset-cli`
- `pyproject.toml` exposes `superset-cli` and not `superset-cli`
- `.github/workflows/ci.yml` uses `superset-cli` commands in smoke checks

**Step 2: Run targeted tests to verify they fail**

Run: `uv run pytest tests/test_cli.py tests/test_config.py tests/test_repo_files.py -v`
Expected: FAIL because the current package metadata, help text, config paths, and CI workflow still use the old name.

### Task 2: Rename the package and entrypoints

**Files:**
- Move: `src/superset_cli/` -> `src/superset_cli/`
- Modify: `pyproject.toml`
- Modify: `devenv.nix`
- Modify: `tests/` imports and monkeypatch targets that reference `superset_cli`

**Step 1: Write minimal implementation**

Rename the Python package directory, update imports, change the package distribution name to `superset-cli`, and expose the console script as `superset-cli = "superset_cli.main:main"`. Update test imports and monkeypatch strings to the new module path. Update `devenv.nix` banner text to the new product name.

**Step 2: Run targeted tests to verify progress**

Run: `uv run pytest tests/test_cli.py tests/test_config.py tests/test_repo_files.py -v`
Expected: some tests may still fail until docs and workflow strings are updated, but package/module references should resolve under the new name.

### Task 3: Rename current docs, workflow checks, and default local paths

**Files:**
- Modify: `src/superset_cli/config.py`
- Modify: `src/superset_cli/cli.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/architecture/README.md`
- Modify: `.github/workflows/ci.yml`

**Step 1: Write minimal implementation**

Update:
- Typer help text to `Superset CLI...`
- default config/state directories to `~/.config/superset-cli/` and `~/.local/share/superset-cli/`
- current README and AGENTS command examples to `uv run superset-cli ...`
- architecture references to the new package path and binary name
- CI smoke-test commands to `superset-cli`

**Step 2: Run targeted tests to verify they pass**

Run: `uv run pytest tests/test_cli.py tests/test_config.py tests/test_repo_files.py -v`
Expected: PASS.

### Task 4: Capture durable rename rationale

**Files:**
- Modify: `docs/decisions/0002-local-config-and-auth-state-storage.md`
- Create: `docs/decisions/0007-superset-cli-product-and-package-name.md`

**Step 1: Update decision records**

Record that the repository now uses `superset-cli` as the product, console command, and package identity, and that the default local config/state paths are intentionally breaking-renamed with no fallback.

**Step 2: Verify decision docs are linked to this work**

Re-read the updated decision records and ensure they reference this plan and the current code paths.

### Task 5: Run full verification

**Files:**
- Verify only

**Step 1: Run focused rename checks**

Run:
- `uv run pytest tests/test_cli.py tests/test_config.py tests/test_repo_files.py -v`
- `uv run superset-cli --help`

Expected: PASS.

**Step 2: Run full repository verification**

Run:
- `uv run pytest -v`
- `uv build`
- `uv run --isolated --no-project --with dist/*.whl superset-cli --help`
- `uv run --isolated --no-project --with dist/*.tar.gz superset-cli --help`

Expected: PASS.

## Decision follow-up

Decision record update required:
- `docs/decisions/0002-local-config-and-auth-state-storage.md`
- `docs/decisions/0007-superset-cli-product-and-package-name.md`
