# 0003: Browser login with Playwright and saved storage state

- Status: accepted
- Date: 2026-06-05
- Related: `src/superset_agent_cli/auth.py`, `src/superset_agent_cli/client.py`, `tests/test_auth.py`, `tests/test_auth_validate.py`, `README.md`

## Context

Self-hosted Superset deployments often use interactive browser-based authentication. The CLI still needs a practical way to reuse authenticated sessions for read-only API access without re-implementing every possible login flow directly in HTTP client code.

## Decision

Use Playwright-driven browser login to establish a real user session, then save browser storage state and reuse its cookies for REST API requests.

The workflow is:
1. launch a browser profile for a configured instance
2. let the user complete login interactively
3. save `storage-state.json`
4. reuse saved cookies for subsequent API validation and read-only requests

## Consequences

- The CLI can work across more Superset login setups than a custom form-based login implementation would support.
- Authentication remains partially manual, which is acceptable for the current bootstrap scope.
- Browser profiles and saved storage state become sensitive artifacts that require careful handling.
- Expired sessions remain a normal operational case and should be handled explicitly in future improvements.

## Alternatives considered

### Implement direct HTTP login only

Rejected because Superset deployments can vary in authentication flow, and a browser-based approach is more robust for bootstrap validation.

### Require the user to export cookies manually

Rejected because it would be more error-prone and less reproducible than saving browser state in a known format.
