# Teach agents the existing authenticated API escape hatch

- Status: todo
- Priority: high
- Type: docs
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/cli.py`, `tests/test_api.py`, `docs/decisions/0011-custom-api-authentication.md`, `docs/tickets/todo/2026-10-06-release-capability-preflight.md`, `docs/tickets/todo/2026-10-06-refresh-companion-skill-recipes.md`

## Context

Verified in source: `api INSTANCE PATH` already provides configured-instance authentication, CSRF handling, query parameters, JSON bodies, and explicit write guards. Recorded agent workflows still extracted cookies and wrote custom HTTP clients. The companion-skill handoff for this feature remained incomplete.

## Definition of done

- [ ] Confirm the chosen installed executable supports `api` before recommending it.
- [ ] Document a read-only request, repeated query parameters, OpenAPI discovery, and an explicitly authorized JSON mutation using the actual command help.
- [ ] Explain that paths must be instance-relative `/api/v1/` paths and that every non-GET request requires literal `--allow-write`, including read-like POSTs.
- [ ] Explain the single bounded browser-cookie recovery attempt, permission/network failure handling, and absence of sent-mutation retries.
- [ ] Update the authoritative companion-skill source and CLI documentation together; never patch deployed skill files.
- [ ] Validate examples with synthetic config/auth and a mock API, covering stdout JSON and write denial.

## Notes

Reuse the existing API command. No new HTTP wrapper, cookie-export recipe, or MCP integration is required. The related skill ticket owns general preflight and stale-recipe cleanup; this ticket owns API-specific recipes.
