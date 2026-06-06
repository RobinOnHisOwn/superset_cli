# AGENTS.md Design

**Date:** 2026-06-05

## Goal

Create a root `AGENTS.md` optimized for coding agents working in this repository, with a strict workflow that emphasizes research-first development, mandatory planning, TDD, minimal diffs, strong verification, and guarded handling of live Superset and auth flows.

## Chosen operating model

- Audience: coding agents only
- Strictness: strict by default, with stronger rules around auth, browser automation, networked behavior, and live Superset validation
- Planning: required before any non-trivial change
- TDD: required for all code changes
- Research: required before implementation, even for familiar tasks
- Live systems: allowed for read-only verification with explicit command logging

## Structure

The `AGENTS.md` file should:
1. describe current repository mission and read-only scope
2. define a mandatory golden workflow
3. list exact working commands near the top
4. encode repo-specific paths and patterns
5. define boundaries with stronger rules for auth and external-system behavior
6. define a concrete definition of done based on evidence

## Repo-specific rules to encode

- prefer `devenv shell` and `uv`
- source lives in `src/superset_agent_cli/`
- tests live in `tests/`
- plans live in `docs/plans/`
- preserve CLI JSON output contracts unless intentionally changed
- for CLI changes, test both human-readable and `--json` output when relevant
- prefer extending existing patterns in `cli.py`, `client.py`, `config.py`, and related tests
- use real Superset instances only for guarded read-only validation
- never commit auth-state or browser-profile artifacts

## Verification standard

For code changes, agents should verify with:
- targeted pytest commands first
- `uv run pytest -v`
- `uv run superset-agent --help`
- `uv build`

For auth/browser/live-instance work, agents should also log exact commands used and state any remaining unverified risk.
