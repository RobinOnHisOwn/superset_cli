# 0022: Explicit server-side list query controls

- Status: accepted
- Date: 2026-10-06
- Related: [plan](../plans/2026-10-06-remaining-open-todos.md), `src/superset_cli/client.py`, `src/superset_cli/cli.py`, `tests/test_list_controls.py`

## Context

Agents currently handwrite API queries for typed filtering, small projections, and complete inventories. FAB exposes resource-specific filter metadata and list column metadata; guessing a universal catalog would reject valid deployments or silently select invalid columns. Some servers cap page size, and concurrent changes can make pagination incomplete.

## Decision

Apply the same optional controls to all 15 paginated resource/security lists:

- Repeat `--filter '{"col":"viz_type","opr":"eq","value":"table"}'`. Exact object keys and finite JSON values are required before access. Values retain JSON types. Generated `q` serializes literal `+`, `%`, and `&` as JSON Unicode escapes so FAB's extra `parse_qs` decode cannot corrupt them; both ordinary JSON and FAB decoding recover the same values. Filters AND together and append to existing `--search`; chart-data `--filter col=value` remains distinct.
- Repeat `--columns FIELD`. Require unique non-empty field identifiers. Validate resource support from list metadata, then request `q.columns` on the server. Human projection output is compact JSON per returned record, avoiding invented missing-field placeholders. Ordinary human/JSON output is unchanged without projection.
- `--all` starts at page zero and rejects explicit `--page`. It defaults to requesting 100 records per page unless a positive `--page-size` is provided; server caps remain authoritative. Preserve filters/projection/order on every page. Prefer ID ordering only if advertised; otherwise preserve explicit or server ordering rather than invent support.

Obtain filter/operator capabilities from `_info`; obtain list/order columns from a one-row list metadata request. These are different endpoints. Malformed metadata and permission failures fail closed. If `_info` returns 404 (Superset 6.1.0's log API omits it), send the syntactically valid filter to the list endpoint's native validation instead; never bypass a 403 or guess a field catalog. FAB 5.2.2 advertises datetime `gt`/`lt`, not a universal `ge` operator. No new network calls are added to ordinary single-page lists without these new controls.

Emit an aggregate `{count, ids, result}` only after every page passes count, identity, duplicate, and progress checks. Use server `ids` independently of projection, falling back to record IDs when available; do not silently add ID to the requested projection. Later-page failures or inconsistent/empty premature pages exit non-zero without printing a partial aggregate. Single-page JSON retains the raw server envelope.

## Consequences

The new controls add small capability reads and buffer an all-page result in memory. Pagination is **not an atomic snapshot**: equal counts and unique IDs cannot detect every concurrent replacement, and non-unique server ordering can still change traversal. Freeze relevant writes or use a server snapshot facility for stronger guarantees; the CLI does not claim one. HTTP timeout/auth/write safety policies remain unchanged.

## Alternatives considered

### Fetch everything and trim locally

Rejected: defeats response-size reduction and hides unsupported server projections.

### Resource-independent filter catalog or mandatory ID ordering

Rejected: fields/operators/order support vary. Superset 6.1.0 charts do not advertise ID ordering.

### Stream pages directly to stdout

Rejected for `--all`: a later failure would leave plausible but incomplete inventory output. Explicit ordinary page calls remain available for streaming clients.
