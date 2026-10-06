# Normalize colored CLI output in test assertions

**Date:** 2026-10-06

## Goal

Keep help and required-option assertions valid with or without terminal colors.

## Planned changes

1. Reproduce PR #4's seven failures with `FORCE_COLOR=1` (verified).
2. Reuse `rich.text.Text.from_ansi(...).plain` from `tests/test_cli.py` in the two affected tests; preserve every semantic and write-guard assertion.
3. Exercise both forced-color and plain-output modes without changing CLI behavior or CI configuration.

## Verification

- Before changes: targeted forced-color run reproduced seven failures.
- Targeted `uv run pytest` run: 14 passed across forced-color and plain-output cases.
- `FORCE_COLOR=1 uv run pytest -v`: 837 passed, 13 optional-browser skips.
- `uv run pytest -v`: 837 passed, 13 optional-browser skips.
- `uv run superset-cli --help`, `uv build`, and `git diff --check`: passed.
- `specdocs_validate`: only the pre-existing architecture README filename error remains.
- GitHub rerun and Linux/Python 3.12 execution remain unverified until the correction is published.

## Decision follow-up

No durable decision change.
