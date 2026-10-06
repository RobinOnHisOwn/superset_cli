# Add security user read commands

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-security-read-surface-design.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Per the security read-surface design, expose read-only user list and detail commands as a thin pass-through to `/api/v1/security/user/` (where exposed by the FAB version on the target Superset).

## Definition of done

- [ ] Client helpers wrap `GET /api/v1/security/user/` and `GET /api/v1/security/user/{pk}`.
- [ ] CLI commands `security users list` and `security users get` exist with JSON and human output.
- [ ] Tests cover JSON, human output, empty list, and not-found.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Completion evidence

Added user list/get reads with ID/username human summaries. Corrected the obsolete singular path assumption: supported FAB APIs use `/api/v1/security/users/`. `tests/test_security_explore_reads.py` covers JSON/human/empty/not-found with synthetic responses. Full suite: 579 passed; CLI help and build passed. README and architecture updated; see ADR 0013. Existing opt-in writes are unchanged.

## Notes

Strictly read-only. Do not include user create/update/delete or password operations. Surface only fields that the authenticated user already sees in the Superset UI.
