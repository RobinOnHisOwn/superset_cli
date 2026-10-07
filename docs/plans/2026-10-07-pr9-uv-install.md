# Remove floating uv version discovery from CI

**Date:** 2026-10-07

## Goal

Fix PR #9's setup failure without changing application code or retrying failed key operations.

## Verified cause and assumptions

- GitHub run 37602686113, job 112730622317 (Python 3.12), failed during `Install uv` fetching `https://raw.githubusercontent.com/astral-sh/versions/main/v1/uv.ndjson`, before dependency installation or tests.
- The same run's Python 3.13 job installed uv 0.12.23 and passed all checks. The failure is not evidence of Python 3.12 incompatibility.
- Pinned setup-uv v8.2.0 source (`src/version/resolve.ts`, `src/version/version-request-resolver.ts`) prioritizes explicit inputs; exact versions resolve without consulting the versions manifest.
- Both CI and release-build workflows omit the uv version and share this exposure. Select the source/live-verified 0.12.23 version for both. Artifact downloads still need network access; this does not eliminate all network failures.

## Planned changes

1. Write a failing repository test requiring an exact, shared uv version on every setup-uv step.
2. Add only `version: "0.12.23"` to existing setup-uv inputs in CI and release workflows. Preserve action SHAs, permissions, Python matrix, publishing gates and all dependency/build commands.
3. Run focused workflow tests, the full suite, help and build; verify exact uv installation and Python 3.12 locally if an interpreter can be made available without repository configuration changes.
4. Report actual local evidence and remote-check status. Do not push or rerun remote workflows contrary to repository write restrictions.

## Verification

All project commands ran from the existing PR worktree through `direnv exec "$PWD"`.

- Red: `uv run pytest tests/test_repo_files.py::test_workflows_pin_a_shared_exact_uv_version -q`: failed because setup-uv had no explicit version.
- Focused: `uv run pytest tests/test_repo_files.py tests/test_release_workflow.py -q`: 12 passed after the two workflow input additions.
- Exact installer verification: `uvx --from uv==0.12.23 uv --version`: uv 0.12.23, installed successfully on macOS ARM64.
- Python 3.12: `direnv exec "$PWD" env UV_PYTHON_INSTALL_DIR=/tmp/pr9-python UV_PROJECT_ENVIRONMENT=/tmp/pr9-venv-py312 UV_PYTHON_DOWNLOADS=automatic UV_PYTHON_PREFERENCE=managed uvx --from uv==0.12.23 uv run --python 3.12 --locked pytest -v`: 1,033 passed, 13 skipped, CPython 3.12.15. Temporary interpreter/environment only; no persistent project/devenv changes. Local devenv defaults disable downloads and require system Python, so both were overridden only for this command. The attempted global `--python-downloads` flag was unsupported; environment settings are the verified invocation.
- Python 3.13: `uvx --from uv==0.12.23 uv run --locked pytest -v`: 1,033 passed, 13 skipped, Python 3.13.12.
- With the exact uv version: `uv run superset-cli --help`, `uv build`, wheel and sdist smoke checks using `uv run --isolated --no-project --with dist/*.whl superset-cli --help` and `--with dist/*.tar.gz`: passed.
- `git diff --check`: passed. Full suite includes relative documentation-link checks; final focused workflow/link checks: 14 passed.
- `specdocs_validate`: reports the existing `docs/architecture/README.md` filename-pattern error in the original workspace; this worktree plan follows the repository template.
- Consulted the existing CI plan and ADR 0011 (PyPI release publishing); their workflow boundaries are unchanged. No application code, dependencies, lockfile, action SHAs, credentials, release gates or permissions changed.
- GitHub checks remain the original failed 3.12 setup / successful 3.13 run until these local changes are published. No PR review comments were present. Linux runner execution of this patch remains unverified; local success is not remote CI success.

## Decision follow-up

No durable decision change.

This is a concrete CI tool-version pin, consistent with existing pinned workflow tooling, not a new release or package policy.
