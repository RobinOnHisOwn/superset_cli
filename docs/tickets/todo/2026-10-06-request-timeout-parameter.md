# Add a per-invocation HTTP timeout parameter

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `docs/decisions/0011-custom-api-authentication.md`, `docs/decisions/0016-api-failure-diagnostics.md`

## Context

August 21 and October 5 Pi conversations used replacement HTTP clients with longer timeouts for query workflows. The current Superset client hardcodes a 30-second timeout. Agents should be able to accommodate slow queries without recreating authentication and CSRF handling. A longer timeout does not fix HTTP 400 errors.

## Definition of done

- [ ] Add an explicit per-invocation `--timeout` in seconds for API-backed workflows, including `api`, chart data, and SQL Lab execution; choose one consistent placement.
- [ ] Validate finite positive values before browser or network access; retain the existing 30-second default.
- [ ] Thread the value through the shared client and verify which authentication, CSRF, and query requests it covers.
- [ ] Document whether the value controls HTTPX phase/inactivity timeouts or a total deadline; do not promise a total runtime bound without implementing one.
- [ ] Preserve bounded authentication recovery and write guards; never retry a sent mutation automatically. Report a mutation timeout as an unknown outcome.
- [ ] Test default/custom timeout forwarding, invalid values, and timeout error output without slow live calls.
- [ ] Write a plan and update CLI help and README examples; record any durable timeout policy.

## Notes

Reuse HTTPX timeout support. Do not add persistent timeout configuration, automatic retries, or a new HTTP abstraction for this task.
