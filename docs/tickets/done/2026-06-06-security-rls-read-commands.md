# Add row-level-security read commands

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-security-read-surface-design.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Per the security read-surface design, expose read-only row-level-security rules.

## Definition of done

- [ ] Client helpers wrap `GET /api/v1/rowlevelsecurity/` and `GET /api/v1/rowlevelsecurity/{pk}`.
- [ ] CLI commands `security rls list` and `security rls get` exist with JSON and human output.
- [ ] Tests cover JSON, human output, empty list, and not-found.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Completion evidence

Added RLS list/get reads through existing CLI helpers. `tests/test_security_explore_reads.py` covers JSON/human/empty/not-found using synthetic transport responses. Full suite: 579 passed; CLI help and build passed. README and architecture updated; see ADR 0013. Existing opt-in writes are unchanged.

## Notes

Strictly read-only. Do not include RLS rule creation, update, or deletion.
