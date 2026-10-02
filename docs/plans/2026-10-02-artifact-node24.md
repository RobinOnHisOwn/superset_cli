# Move release artifact actions to Node.js 24

**Date:** 2026-10-02

## Goal

Remove the deprecated Node.js 20 action declaration from release artifact upload/download without changing publishing behavior.

## Verified facts

- `main` now includes the original release implementation and ANSI-help fix; work starts from freshly fetched `origin/main` in `fix/artifact-node24`.
- GitHub reports latest releases `actions/upload-artifact` v7.0.1 and `actions/download-artifact` v8.0.1.
- Resolved commit pins are `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` and `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`, respectively. Both release manifests declare `runs.using: node24`.
- Upload still defaults to archived (zipped) artifacts; download defaults to decompressing them. Existing `name: distributions` / `path: dist/` inputs remain supported. Download now fails on digest mismatch by default; do not relax that safeguard.
- Workflows use GitHub-hosted Ubuntu runners, not self-hosted runners. Consulted ADR 0011; commit pinning, job isolation and OIDC permissions remain unchanged.

## Planned changes

1. Add regression checks for the audited Node.js 24 artifact-action pins in `tests/test_release_workflow.py`; confirm they fail against current v4 pins.
2. Change only the upload/download action refs and version comments in `.github/workflows/publish.yml`.
3. Run focused tests, full pytest, CLI help, build and actionlint. Verify artifact inputs and publishing permissions remain unchanged.

## Verification

- `uv run pytest tests/test_release_workflow.py -v` (red, then green).
- `uv run pytest -v`, `uv run superset-cli --help`, `uv build`.
- `actionlint .github/workflows/ci.yml .github/workflows/publish.yml` and `git diff --check`.
- GitHub workflow execution remains unverified until the update is published and a build is run.

## Results

- Regression tests first failed against both old v4 pins (2 failed, 6 passed).
- Focused tests after the update: 8 passed.
- Full suite: 471 passed on macOS / Python 3.13.
- CLI help, wheel/sdist build, actionlint for both workflows and `git diff --check`: passed.
- Actual GitHub action execution remains pending; no commit, push, remote settings change or publishing was performed.

## Decision follow-up

No durable decision change.
