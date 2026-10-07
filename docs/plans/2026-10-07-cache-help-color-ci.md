# Fix cache help assertions under colored CI output

**Date:** 2026-10-07

## Goal

Fix PR #8's sole CI failure without changing runtime behavior or weakening the write-guard assertion.

## Verified cause

Both Python 3.12 and 3.13 CI jobs fail in `test_cache_help_explains_write_guard`: ANSI styling separates the hyphens in `--allow-write`. Local forced-color execution reproduces the failure. Existing `tests/test_cli.py` normalizes help with `rich.text.Text.from_ansi(...).plain` and tests both color modes. The existing decision `docs/plans/2026-10-06-ci-colored-output.md` covers this testing policy; no runtime decision changes.

## Planned changes

1. Parameterize the cache help test for forced-color and no-color environments and confirm the colored case fails before normalization.
2. Reuse the existing ANSI normalization pattern, preserving both flag and dry-run assertions. Assert forced-color output actually contains ANSI escapes.
3. Add concise CLI output/CI verification guidance to `AGENTS.md`.
4. Run focused tests, default and forced-color full suites, help smoke check, and build. Update only the existing PR feature branch; do not merge or publish a package.

## Verification

- Before normalization: parameterized help test reproduced one colored failure and one plain pass.
- Focused cache/CLI tests: 56 passed.
- `FORCE_COLOR=1 uv run pytest -v`: 997 passed, 13 optional-browser skips.
- `uv run pytest -v`: 997 passed, 13 optional-browser skips.
- CLI help, wheel/sdist build, and `git diff --check`: passed.
- Local runs use macOS/Python 3.13; Linux/Python 3.12 and 3.13 results require the PR CI rerun after pushing. Do not infer their success from local output.
- `specdocs_validate` reports only the existing architecture README naming-convention mismatch in the harness working directory.

## Decision follow-up

No durable decision change.
