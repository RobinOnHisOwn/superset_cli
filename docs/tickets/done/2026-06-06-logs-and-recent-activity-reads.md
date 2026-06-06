# Add log and recent-activity read commands

- Status: done
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes log list, log detail, and recent-activity reads, but the CLI currently has no operational activity inspection commands. These endpoints would help agents investigate usage and recent changes while staying within a read-only posture.

## Definition of done

- [x] A CLI resource group exposes log list and detail reads, plus recent-activity inspection if the contract fits naturally.
- [x] Client helpers wrap the corresponding Superset log read endpoints.
- [x] Tests cover human output, JSON output, and guard behavior.
- [x] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Prefer a minimal initial surface instead of exposing every log-adjacent endpoint at once.
