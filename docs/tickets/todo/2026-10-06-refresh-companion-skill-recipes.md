# Refresh companion-skill preflight and command recipes

- Status: todo
- Priority: high
- Type: docs
- Created by: agent
- Created at: 2026-10-06
- Related: `README.md`, `src/superset_cli/cli.py`, `docs/tickets/todo/2026-10-06-release-capability-preflight.md`, `docs/tickets/todo/2026-10-06-document-api-escape-hatch.md`, `docs/tickets/todo/2026-10-06-dashboard-render-verification-recipe.md`, `docs/tickets/todo/2026-08-27-session-scoped-cookie-unreadable-from-firefox-zen.md`

## Context

The companion skill's chart-update and dashboard-diff examples omit required instance arguments. A separate workaround skill describes missing CSRF support and missing Zen auto-detection as general limitations even though current CLI source has fixes. These discrepancies promote failing commands and unnecessary replacement HTTP clients.

Skill sources are maintained separately from their deployed copies. This repository should track the handoff without duplicating another skill catalog.

## Definition of done

- [ ] Locate and update the authoritative companion-skill and related workaround-skill sources, not deployed files.
- [ ] Validate command recipes against actual help: include the instance in `charts update INSTANCE CHART_ID` and `dashboards diff INSTANCE A B`.
- [ ] Add a short executable/provenance/capability preflight, JSON-first discovery, and precise command ordering without querying help redundantly on every invocation.
- [ ] Route custom requests through the existing authenticated API recipe and browser verification through the optional rendering recipe.
- [ ] Retire obsolete unconditional CSRF/auto-detection workarounds or explicitly gate them to verified legacy capabilities.
- [ ] Explain stale saved query context after params edits, including the clear-context operation's write guard and the difference between persistence, query correctness, and visible rendering.
- [ ] Exercise corrected examples with a mock API and verify an agent can complete a representative workflow without manual cookie extraction or repeated stale-auth retries.

## Notes

Coordinate release and skill rollout. Keep ownership clear: related tickets own detailed API, auth, release, and rendering acceptance checks; this ticket integrates their pointers and fixes general recipe drift.
