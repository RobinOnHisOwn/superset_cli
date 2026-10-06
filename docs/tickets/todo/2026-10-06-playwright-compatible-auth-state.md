# Provide validated Playwright-compatible auth state

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/auth.py`, `src/superset_cli/client.py`, `tests/test_auth.py`, `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`, `docs/tickets/todo/2026-10-06-dashboard-render-verification-recipe.md`

## Context

Recorded browser-verification workflows failed because saved cookie expiry values were not acceptable Playwright Unix timestamps in seconds. Agents repeatedly patched temporary render scripts to convert expiry units and supply cookie fields. Verified in source: cookie serialization copies `expires` as a float without unit normalization.

The exact source formats and existing-state compatibility are prerequisites to verify, not assumptions that every browser uses milliseconds.

## Definition of done

- [ ] Reproduce with synthetic browser-cookie inputs and inspect the supported loaders' expiry units and session-cookie conventions.
- [ ] Choose the smallest compatible solution: normalize serialization or provide an explicit export without silently breaking existing state consumers.
- [ ] Handle verified seconds/milliseconds formats, session cookies, absent expiry, and invalid values; retain required cookie attributes when available.
- [ ] Test existing-state compatibility and run an actual Playwright context-loading smoke check against synthetic, non-secret exported state.
- [ ] Keep Playwright optional/test-only, not a default runtime dependency or replacement login flow.
- [ ] Document secret-safe use of the exported state and any existing-state migration requirement.

## Notes

Follow ADR 0008. Obtain approval before changing dependencies or JSON contracts. Never inspect or print real cookie values in tests or documentation.
