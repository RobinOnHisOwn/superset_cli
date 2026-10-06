# Implement read-only export commands

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-read-only-export-commands.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

The design ticket `2026-06-06-read-only-export-commands.md` proposed read-only export commands for dashboards, charts, datasets, and databases. This ticket implements that design.

## Definition of done

- [ ] `SupersetClient` gains a binary GET helper that returns `(bytes, content_type, status)` and reuses the existing 401 / 404 handling without forcing a `response.json()` call.
- [ ] CLI commands exist:
  - [ ] `dashboards export <instance> <id...> --output <path> [--force]`
  - [ ] `charts export <instance> <id...> --output <path> [--force]`
  - [ ] `datasets export <instance> <id...> --output <path> [--force]`
  - [ ] `databases export <instance> <id...> --output <path> [--force]`
- [ ] All commands validate that the response is a ZIP before writing the output file.
- [ ] Refuses to overwrite an existing file unless `--force` is supplied.
- [ ] Tests cover happy path, non-zip response, overwrite refusal, `--force`, network error, 404.
- [ ] `README.md` and `docs/architecture/README.md` are updated.
- [ ] A decision record is added describing the JSON vs. binary response handling rule for `SupersetClient`.

## Completion evidence

Added binary GET and all four export commands, positive ID/Rison encoding, ZIP validation, and no-overwrite defaults. `tests/test_exports.py`: 31 passed, covering success, force/refusal, invalid archives/IDs, auth/not-found, and network failure. Full suite: 579 passed; CLI help and build passed. README and architecture updated; see ADR 0014.

## Notes

Reference the design document for the exact endpoints, `q` rison encoding, and risks to avoid.
