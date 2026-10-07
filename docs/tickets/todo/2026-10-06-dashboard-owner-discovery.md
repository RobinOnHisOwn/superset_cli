# Inspect dashboard owners and discover eligible owners

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_dashboards_get.py`, `docs/tickets/todo/2026-06-06-security-users-read-commands.md`, `docs/tickets/todo/2026-10-06-dashboard-owner-replacement.md`

## Context

Dashboard ownership is a collection, not a single owner. Existing `dashboards get --json` forwards dashboard details, but human output does not show owners. Superset 6.0 exposes owner IDs and names in dashboard details and supports eligible-owner discovery through the dashboard related-field API. Avoid requiring the separately planned security user directory: that API may be disabled or require additional permissions.

## Definition of done

- [ ] Write an implementation plan and failing tests before code changes.
- [ ] Verify the supported Superset version's OpenAPI and related-field query contract before selecting command names and output shapes.
- [ ] Provide focused read-only owner inspection with IDs and names, human and JSON output, including an empty owner list. Reuse `get_dashboard`; preserve existing dashboard JSON contracts.
- [ ] Provide eligible-owner discovery using `GET /api/v1/dashboard/related/owners`, with verified search and pagination behavior; preserve the server's permission filtering and result envelope.
- [ ] Test ID/slug reads, candidate pagination, empty results, missing dashboard, expired auth, and permission denial. Do not treat unavailable owner fields as an empty owner list.
- [ ] Document that owners are distinct from creators, last modifiers, viewers, dashboard roles, and chart/dataset owners.
- [ ] Update README and architecture command mappings; run targeted tests, full pytest, CLI help smoke checks, and build.

## Notes

Research performed on 2026-10-06; no live instance was accessed.

**Verified:** Superset 6.0 includes `owners` in `DashboardGetResponseSchema`; dashboard API allows related field `owners` with related-user filtering. Current upstream master instead uses `editors`/`viewers` and subject IDs. Do not silently map user IDs to subject IDs or treat editors as identical to owners.

**Proposed:** Focused owner commands alongside existing dashboard reads, using server-returned IDs rather than ambiguous name matching.

**Unknown:** Target deployment version, related-field search semantics, and authenticated user's permissions. Inspect its OpenAPI using existing `openapi fetch` before implementation; do not launch browser login without announcing it.

Sources:
- https://github.com/apache/superset/blob/6.0.0/superset/dashboards/api.py
- https://github.com/apache/superset/blob/6.0.0/superset/dashboards/schemas.py
- https://github.com/apache/superset/blob/master/superset/dashboards/schemas.py
