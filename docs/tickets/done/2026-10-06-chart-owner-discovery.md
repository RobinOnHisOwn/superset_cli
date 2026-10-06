# Inspect chart owners and discover eligible owners

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `docs/tickets/done/2026-10-06-dashboard-owner-discovery.md`, `docs/tickets/done/2026-10-06-chart-owner-replacement.md`, `docs/tickets/done/2026-06-06-security-users-read-commands.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_charts_get.py`

## Context

Charts have their own owner collection, independent of dashboard and dataset ownership. Existing `charts get --json` forwards chart details, but human output does not show owners. Superset 6.0 exposes owners in chart details and permits eligible-owner discovery through the chart related-field API. Reuse existing reads rather than depending on a security user directory that may be disabled or require broader permissions.

## Definition of done

- [x] Write an implementation plan and failing tests before code; approve proposed command names and output contracts.
- [x] Verify supported-version OpenAPI and related-field query semantics before implementation.
- [x] Provide focused read-only chart owner inspection with IDs/names and human/JSON output, reusing `get_chart` and preserving existing chart JSON contracts.
- [x] Support existing numeric-ID/UUID chart reads; distinguish an empty owner list from a missing or unsupported owner field.
- [x] Discover eligible owners through `GET /api/v1/chart/related/owners`, with verified search/pagination and preserved server permission filtering and response envelope.
- [x] Test multiple owners, empty results, ID/UUID lookup, pagination, missing chart, expired auth, permission denial, and unavailable owner fields.
- [x] Document that chart owners are not dashboard owners, dataset owners, creators, last modifiers, or viewers; do not expose user administration writes.
- [x] Update README and architecture mappings; run targeted tests, full pytest, CLI help smoke checks, and build.

## Completion evidence

Implemented `charts owners` and `owner-candidates` with existing detail GET, positive owner-ID/schema validation, permission-filtered related reads, verified `filter/page/page_size` query shape, and preserved candidate envelope. Empty and missing fields are distinct. Source contract verified against Superset 6.0 schemas/base API/filter code; target capability checks run at invocation, with no live instance probe. **187 owner tests and 843 full-suite tests passed**, build/help/guard smoke checks passed. Plan: `docs/plans/2026-10-06-owner-management.md`; ADR 0020. Existing `charts get --json` unchanged.

## Notes

Research on 2026-10-06; no live instance was accessed.

**Verified:** Superset 6.0's `ChartGetResponseSchema` includes owner objects. Its chart API allows the related field `owners` and applies related-user filtering. Current upstream master instead uses `editors`/`viewers` with subject IDs.

**Proposed:** ID-based focused owner reads and candidate discovery, consistent with the dashboard owner work where contracts actually match.

**Unknown:** Target deployment version, candidate search semantics, and permissions. Inspect existing `openapi fetch` output before implementation; do not silently map user IDs to subject IDs or interpret missing owners as an empty list.

Sources:
- https://github.com/apache/superset/blob/6.0.0/superset/charts/api.py
- https://github.com/apache/superset/blob/6.0.0/superset/charts/schemas.py
- https://github.com/apache/superset/blob/master/superset/charts/schemas.py
