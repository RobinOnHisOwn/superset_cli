# ANSI-safe CLI help test

**Date:** 2026-10-02

## Goal

Keep the write-safety help assertion valid with both plain and ANSI-colored output.

## Verified facts

- GitHub CI run `36984597282` fails on Python 3.12 and 3.13 at `tests/test_cli.py::test_help_advertises_allow_write_safety`.
- ANSI sequences split the displayed `--allow-write` flag in the raw captured string. `FORCE_COLOR=1` reproduces the same failure locally before changes.
- The installed Typer depends on Rich; Click is not separately installed. Rich exposes public `Text.from_ansi(...).plain` for decoding styled text. No new dependency is needed.
- Consulted ADR 0009: the help assertion must continue checking the exact `--allow-write` safety flag.

## Planned changes

1. Parameterize the existing help test for ordinary and forced-color rendering, with fixture-managed environment variables; assert forced-color output really contains ANSI sequences.
2. Run the expanded test before normalization and confirm the forced-color case fails on the existing literal assertion.
3. Decode captured help using `rich.text.Text.from_ansi(...).plain` before the existing content assertions. Do not change CLI behavior, dependencies, or safety expectations.
4. Run focused tests, then the full suite with and without forced color; run CLI help, build, and isolated artifact smoke checks. Record verification results.

## Verification

- `uv run pytest tests/test_cli.py -v` (red, then green).
- `uv run pytest -v` and `FORCE_COLOR=1 uv run pytest -v`.
- `uv run superset-cli --help`, `uv build`, isolated wheel/sdist installation checks, and `git diff --check`.
- Actual GitHub execution remains unverified until the fix is published and CI reruns.

## Results

- Original test reproduced the CI failure with `FORCE_COLOR=1`.
- Expanded test before normalization: plain case passed, forced-color case failed on the exact flag assertion.
- `uv run pytest tests/test_cli.py -v`: 5 passed after normalization.
- `uv run pytest -v`: 469 passed on macOS / Python 3.13.
- `FORCE_COLOR=1 uv run pytest -v`: 469 passed.
- CLI help, wheel/sdist builds, isolated wheel/sdist install-and-help smoke checks, and `git diff --check`: passed.
- Only `tests/test_cli.py` and this plan changed; no CLI behavior, dependency, lockfile, or durable decision change. GitHub CI rerun remains pending.

## Decision follow-up

No durable decision change.
