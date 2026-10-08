# superset-cli

CLI for self-hosted Apache Superset.

[MIT licensed](LICENSE). Copyright (c) 2026 Robin Rittsteiger.

## Scope

Current scope (read by default, write opt-in):
- Python project managed with `uv`
- `devenv` shell configured for Python + uv
- local instance config management (add, list, remove)
- browser-cookie import login with immediate live validation + saved auth-state inspection
- read access to dashboards, charts, datasets, databases, annotation layers, CSS templates, themes, tags, reports, saved queries, queries, logs, permalinks, OpenAPI, embedded configs, related objects, chart data
- write access to chart, dashboard, dataset, database, saved-query, SQL Lab, tag, theme, security (roles, users, RLS), and asset-import surfaces; **every write command requires `--allow-write` on every invocation** (see [ADR 0009](docs/decisions/0009-write-command-explicit-opt-in.md) and [ADR 0010](docs/decisions/0010-write-scope-expansion.md))
- shared list-query controls on all list commands via `--page` (0-based), `--page-size`, `--search`, `--order-column`, and `--order-direction`
- user-friendly error messages for auth expiry, missing resources, and network failures (exit code 1, no raw tracebacks)

## HTTP timeouts

Use the root `--timeout SECONDS` option **before the command** for slow API requests:

```bash
superset-cli --timeout 90 charts data prod 7 --json
superset-cli --timeout 90 api prod /api/v1/dashboard/
```

The default remains 30 seconds. Values must be finite and positive. The option
applies to API requests, authentication validation/recovery, CSRF acquisition,
and JWT login/refresh. It controls HTTPX connect/read/write/pool phase or
inactivity timeouts, **not a total command deadline**. It is not saved in config.
A timeout exits non-zero; a sent mutation's outcome is unknown. Check server
state before retrying. The CLI never automatically retries a sent mutation;
`--allow-write` is still required on every write invocation.

## Decision log

Long-lived technical reasoning lives in `docs/decisions/`.

Use it to understand why key choices were made, not just what the code does. Start with `docs/decisions/README.md`.

## Documentation map

A top-level map of repository docs lives in `docs/index.md`.
A glossary of repository-specific terms lives in `docs/glossary.md`.

## Architecture

A structural overview of modules, command-to-code mappings, and test entry points lives in `docs/architecture/README.md`.

## Installation for users

Install the published CLI without cloning this repository:

```bash
uv tool install superset-cli
superset-cli --help
```

Upgrade with `uv tool upgrade superset-cli`. Python 3.12 or newer is required;
uv can provision Python when needed. `pipx install superset-cli` is an alternative.
PyPI `0.1.0` was verified on 2026-10-06: its wheel includes the API command, CSRF handling, validated cookie-import fallback, and `--clear-query-context`, but no `--version` flag. A local installation also labeled `0.1.0` lacked those capabilities; version labels alone are insufficient. PyPI **0.2.0** was rechecked on 2026-10-07 and includes `--version`, owners, CSRF handling, and Playwright export. This checkout builds distinct unpublished **0.3.0** artifacts with the new cache controls. An isolated upgrade from 0.1.0 through 0.2.0 to the built 0.3.0 wheel preserved synthetic config/auth files; no publication was performed.

Check `command -v superset-cli`, then its installation owner (`uv tool list` or `pipx list`). If it is installed but missing from PATH, use `uv tool update-shell` or `pipx ensurepath` rather than installing another copy. Upgrade with the same tool (`uv tool upgrade superset-cli` or `pipx upgrade superset-cli`). Config/auth files remain separate from the package installation. Check `api --help` and `charts update --help` once per session for required capabilities; use `--version` when available. Inside this source checkout, select `uv run superset-cli` explicitly.

## Publishing releases (maintainers)

The canonical upstream is [RobinOnHisOwn/superset_cli](https://github.com/RobinOnHisOwn/superset_cli),
owned by the `RobinOnHisOwn` organization. The company repository is a mirror, not
an independent publishing source.

Before the first release:

1. Confirm ownership and permission to publish from the canonical repository,
   and review source and Git history for sensitive material. MIT licensing is configured
   in `LICENSE` and the distribution metadata.
2. Keep this repository excluded from shared self-hosted runner groups. CI and publishing
   use GitHub-hosted `ubuntu-latest` runners.
3. Create a GitHub environment named `pypi` with required reviewer approval and
   restrict deployment to tags matching `v*` (no branches). A sole maintainer can
   select themselves as reviewer with prevent-self-review disabled. On Free/Pro/Team,
   required reviewers are available only for public repositories; configure this gate
   after making the reviewed repository public, before publishing. Protect release
   tags and `main` against unauthorized changes.
4. Configure a pending [PyPI Trusted Publisher](https://pypi.org/manage/account/publishing/)
   with project `superset-cli`, owner `RobinOnHisOwn`, repository `superset_cli`, workflow filename
   `publish.yml`, and environment `pypi`. Do not create an API-token secret.
   Configure only the canonical repository, not mirrors.

For each release, update `project.version` in `pyproject.toml` and regenerate `uv.lock`
with `uv lock`; have the change reviewed and CI pass. Run **Build and publish** manually
for a build-only rehearsal. Publish a GitHub release from the reviewed commit with a
matching tag (for example `v0.1.0` for version `0.1.0`), then approve the `pypi`
environment deployment. Manual runs never publish; published releases build and test
before publishing the same artifacts. PyPI versions cannot be overwritten: use a new
version for changed distributions. Prereleases also publish, so use a corresponding
version such as `0.2.0rc1` and tag `v0.2.0rc1`.

See [ADR 0011](docs/decisions/0011-pypi-release-publishing.md) for the security rationale.

## Quick start for contributors

If you use `direnv`, allow the repo once and `devenv` will auto-activate whenever you enter this directory.

```bash
direnv allow
uv sync --group dev
uv run superset-cli --help
uv run pytest -v
```

Without `direnv`, enter the shell manually:

```bash
devenv shell
```

## Custom authenticated API calls

```bash
uv run superset-cli api prod /api/v1/_openapi --json
uv run superset-cli api prod /api/v1/dashboard/ --param 'q={"page":0,"page_size":10}' --json
uv run superset-cli api prod /api/v1/chart/42 --method PUT --file /tmp/chart.json --allow-write --json
```

Replace the instance and IDs with discovered values; the write example is not permission to execute it.
GET is the default. POST, PUT, PATCH, and DELETE require `--allow-write`, including read-like POST calls.
Use repeated `--param KEY=VALUE` options and JSON object bodies through `--body`, `--body -` (stdin), or `--file`.
Responses preserve the full API envelope: `--json` emits compact JSON, otherwise pretty JSON.

The command validates the saved session before sending the request. Missing or rejected authentication triggers one browser-cookie import attempt with live validation; select a browser with `--browser zen` if needed.
You must already be signed in in that browser. Recovery progress goes to stderr; no browser is launched and sent mutations are never retried. Network errors and permission failures do not trigger recovery.
Only instance-relative `/api/v1/` paths are accepted and redirects are not followed. Custom requests handle CSRF automatically. Existing commands retain their explicit login behavior.

## Instance selection

When the positional instance is omitted, precedence is global `--instance`,
`SUPERSET_CLI_INSTANCE`, persisted `default_instance`, then the sole configured
instance. A supplied positional instance always wins for fixed-arity commands.
Unknown selected names and multiple instances without a default fail explicitly.
`instances list` shows a persisted default; its JSON adds `default_instance` only
when one is configured. Removing that instance clears the default.

```bash
uv run superset-cli instances use prod
uv run superset-cli instances use --show
uv run superset-cli --instance prod charts get 10 --json
uv run superset-cli charts list --json
uv run superset-cli instances use --clear
```

Variadic exports treat numeric positionals as IDs when global `--instance` is
provided. If a numeric value could be either a configured instance name or an
export ID, the CLI refuses to guess: use `--instance NAME` and supply only IDs.

## JWT authentication (DB/LDAP only)

Browser cookies remain the default. Deployments accepting direct DB or LDAP
login can use JWT instead; OAuth/OIDC/SAML/REMOTE_USER are not supported by the
JWT login endpoint. Supply credentials through existing environment variables,
never command-line password values or config-file secrets.

```bash
uv run superset-cli auth jwt login prod --username-env EXAMPLE_USER --password-env EXAMPLE_PASSWORD
uv run superset-cli auth jwt refresh prod
uv run superset-cli auth status prod --json
uv run superset-cli auth jwt logout prod
```

Successful JWT login stores only environment-variable bindings/provider in the
instance's `auth` config and selects `mode: jwt`. Tokens live in private
`jwt-state.json` (0600), separately from browser state. `auth status` reports only
expiry claims, which are unverified and display-only; it never prints tokens.
JWT GET requests get one refresh-and-retry on 401. Sent writes are never retried;
refresh explicitly before rerunning an authorized write. CSRF handling remains
required for modifying Superset APIs, including JWT calls. Logout removes JWT
state only. To return to browser auth, set `auth.mode: cookie` in the instance
config and use the normal browser login flow. JWT API calls never import browser
cookies automatically. JWT login/refresh/API calls require HTTPS, except HTTP
loopback development (`localhost` or loopback IP literals); embedded URL
credentials and malformed bearer values are rejected without echoing secrets.
Updating an instance URL preserves its selected auth mode and bindings.

## API-key authentication (capability-gated)

The source-verified combination is **Superset 6.1.0 with Flask-AppBuilder 5.2.2**,
`FAB_API_KEY_ENABLED=True`, initialized key storage, an active issued key, and a
matching prefix. Superset's version alone does not guarantee support. No real
API-key deployment was exercised during implementation; see [ADR 0023](docs/decisions/0023-environment-bound-api-keys.md).

Provide an existing issued key through a secure environment injector, never a
literal CLI argument or config value. Register only its environment-variable name:

```bash
superset-cli auth api-key set prod --env EXAMPLE_SUPERSET_API_KEY --json
superset-cli auth validate prod --json
superset-cli charts list prod --json
superset-cli auth api-key clear prod --json
```

`set` verifies a read-only `/api/v1/me/` request before saving the binding. Use
`--prefix` if the server's configured prefix differs from `sst_`. The CLI does not
enable server flags or upgrade server dependencies; guarded current-user creation is described below. Unsupported
or rejected authentication fails without saving a binding or browser/JWT fallback.
Keys are reread from the environment per invocation and never saved in auth files.
HTTPS is required except loopback HTTP development; redirects and embedded URL
credentials are rejected. CSRF, timeouts, and per-invocation `--allow-write` remain
required as applicable; sent mutations never replay. `auth status` reports local
credential availability, not current server acceptance. `clear` returns to cookie
mode without deleting cookie/JWT files. Selecting API-key mode replaces prior auth
bindings; clearing it does not restore JWT credential bindings or the previous mode.
Reconfigure JWT explicitly when switching back. API keys cannot be exported to Playwright.

### Current-user API-key lifecycle

```bash
superset-cli auth api-key list prod --json
superset-cli auth api-key get prod 12345678-1234-4234-8234-123456789abc --json
superset-cli auth api-key revoke prod 12345678-1234-4234-8234-123456789abc --allow-write --json
```

Native FAB endpoints operate only on the authenticated user's keys; no `--user`
option. They require enabled/initialized key support and `can_list`, `can_get`,
or `can_revoke` on `ApiKey`, respectively. Revoke also requires `can_get` for
preflight/read-back and the existing CSRF permission. Use a separate authorized
credential belonging to the same user when revoking a key. Do not grant key
management to the minimal cache runtime role.

List has no pagination. JSON is `{"result": [...]}` for list and
`{"result": {...}}` for get/revoke, containing only native metadata: UUID, name,
prefix, scopes, active flag and creation/expiry/revocation/last-use timestamps.
Plaintext keys, hashes and unexpected fields are excluded. `active` alone is not
a guarantee of validity; stored scopes are not dataset isolation. Human reads
show the same metadata; revoke reports verification.

Revoke requires literal `--allow-write` before credential/network access. HTTP
200 alone is insufficient: success requires matching UUID read-back with
`active=false` and a valid `revoked_on` timestamp. This confirms stored state,
not a separately tested live request rejection. Timeouts, failed read-back
(including self-revocation), or missing evidence exit non-zero as **unverified**.
Reconcile using an independent authorized credential before retrying; the key
may already be revoked. Mutations are never replayed. Current-user creation uses the guarded 1Password workflow below; no plaintext
issuance or guessed cross-user integration is exposed. Local `set`/`clear`
binding behavior is unchanged.

### Create a current-user API key

```bash
uv run superset-cli auth api-key create --help
```

`auth api-key create` requires the instance and `--name`, `--expires-on`,
`--operation-id`, `--server-timezone`, `--op-account`, `--op-vault`, and literal
`--allow-write`. Use an already authenticated provisioning identity belonging
to the intended user. Native FAB cannot target another user. The four
`can_list/create/get/revoke` grants on `ApiKey`, CSRF read access, an active caller
and working `/me/roles/` metadata are required; do not grant these to cache-runtime callers.

Expiry input must be timezone-aware ISO, future and within 90 days. FAB 5.2.2
stores naive timestamps and compares them with the server's local clock.
`--server-timezone` must be the independently verified server IANA clock timezone:
never assume UTC. The CLI converts the input instant to that wall time and rejects
ambiguous DST folds. Read-back must confirm the exact stored expiry. `--prefix`
selects the expected server prefix (default `sst_`); stored scopes are not authorization.

Initially supports the inspected **1Password CLI 2.33.1**. Account/vault selection
is mandatory. Before issuing a key, create/read/edit a new non-secret placeholder
to verify destination permissions. Then deliver to its immutable item/vault IDs
through captured stdin JSON, and read back with reveal plus cache disabled to
verify the concealed credential, key UUID, caller and instance metadata. No key
is printed, written to a plaintext file, passed in argv, or added to the process
environment. Existing local auth bindings are not replaced. Python does not
guarantee memory zeroization.

`--operation-id` is a new unique UUID for a new operation, embedded in the server
key name and dedicated item title. Do not share it concurrently, regenerate it
following failure, or blindly rerun a timed-out invocation. Existing server
markers are refused, but native names are **not** backend idempotency guarantees:
a late request may complete after reconciliation. Inspect current-user key
metadata and the 1Password marker with a surviving credential before recovery.

If delivery fails, attempt owner-scoped reconciliation and verified revocation
using the original caller. Unknown issuance, multiple matches, interruptions or
cleanup failure remain non-success with recovery IDs; an uncatchable process
termination can prevent rollback. Placeholder/item deletion is best-effort and
reported as requested, not proven. No atomicity spans Superset and 1Password.

Successful `--json` output contains only `operation_id`, `key_uuid`, `item_id`,
`vault_id`, `stored`, `revocation_verified`, `outcome`, and `item_cleanup`.
Workflow failures return the same safe recovery fields and exit non-zero;
argument/config/auth preflight errors keep existing CLI conventions. Human
success reports UUID/item/vault only. Creation success verifies stored state
and delivery, not observed authentication with the new key. Live disposable-vault
and Superset release acceptance remains unverified. See
[ADR 0025](docs/decisions/0025-current-user-api-key-creation.md).

## Resource list controls

All 15 resource/security lists support optional `--filter`, `--columns`, and `--all`.
`instances list` is local, not paginated. Ordinary single-page output is unchanged.

```bash
superset-cli charts list prod --filter '{"col":"viz_type","opr":"eq","value":"table"}' --columns id --columns slice_name --json
superset-cli logs list prod --filter '{"col":"dttm","opr":"gt","value":"2026-01-01"}' --json
superset-cli dashboards list prod --all --page-size 100 --json
```

Repeat JSON-object filters with exactly `col`, `opr`, and `value`. Values retain
JSON types (strings, numbers, booleans, null, arrays); filters AND together and
append to `--search`. This is distinct from chart-data `--filter col=value`.
Resource `_info` determines supported fields/operators; unsupported combinations
fail rather than using a guessed universal catalog. When a resource omits `_info`
(as Superset 6.1.0 logs do), the list endpoint validates the filter directly.
Permission failures never trigger this fallback.

Repeat `--columns FIELD` once per unique field. Resource list metadata is checked
before requesting `q.columns` on the server. Projected human output is compact
JSON per returned row, so omitted default fields do not produce `None` placeholders.
Single-page `--json` preserves the server envelope.

`--all` starts at page zero, rejects explicit `--page`, and requests 100 records
per page unless `--page-size` is given. Server caps are respected. Filters,
projection, and ordering persist across pages; ID ordering is preferred only
when advertised, otherwise explicit/server ordering is retained. Server `ids`
allow duplicate checks without adding an unrequested ID field to the projection.
The aggregate JSON envelope is exactly `{count, ids, result}`. No aggregate is
printed if a later page fails, counts change, identities duplicate, or pages stop
early. **This is not an atomic snapshot**: non-unique ordering and concurrent
changes can still affect completeness even when checks pass. Buffering `--all`
uses memory proportional to the result. Capability checks add small read requests;
legacy single-page lists without new controls add none. See [ADR 0022](docs/decisions/0022-explicit-list-query-controls.md).

## Current commands

```bash
uv run superset-cli instances add prod https://superset.example.com
uv run superset-cli instances list --json
uv run superset-cli instances remove prod --json
uv run superset-cli auth login prod                          # auto-detect: chrome -> edge -> brave -> firefox -> zen -> safari
uv run superset-cli auth login prod --browser firefox        # read cookies from Firefox
uv run superset-cli auth login prod --browser zen --json     # read cookies from Zen Browser
uv run superset-cli auth logout prod --json
uv run superset-cli auth status prod --json
uv run superset-cli auth validate prod --json
uv run superset-cli openapi fetch prod --json
uv run superset-cli me show prod --json
uv run superset-cli me roles prod --json
uv run superset-cli dashboards list prod --json
uv run superset-cli dashboards list prod --page 0 --page-size 25 --json
uv run superset-cli dashboards list prod --search Revenue --order-column dashboard_title --order-direction asc --json
uv run superset-cli dashboards get prod 7 --json
uv run superset-cli dashboards diff prod 7 8 --json           # field-by-field record comparison
uv run superset-cli dashboards charts prod 7 --json
uv run superset-cli dashboards datasets prod 7 --json
uv run superset-cli charts list prod --json
uv run superset-cli charts list prod --page 1 --page-size 10 --json
uv run superset-cli charts list prod --search Revenue --order-column slice_name --order-direction desc --json
uv run superset-cli charts get prod 42 --json
uv run superset-cli datasets list prod --json
uv run superset-cli datasets list prod --page 0 --page-size 50 --json
uv run superset-cli datasets list prod --search orders --order-column table_name --order-direction asc --json
uv run superset-cli datasets get prod 5 --json
uv run superset-cli databases list prod --json
uv run superset-cli databases list prod --page 0 --page-size 10 --json
uv run superset-cli databases list prod --search analytics --order-column database_name --order-direction desc --json
uv run superset-cli databases get prod 1 --json
uv run superset-cli databases schemas prod 1 --json
uv run superset-cli databases tables prod 1 --schema analytics --json
uv run superset-cli dashboards embedded prod 7 --json
uv run superset-cli datasets related prod 21 --json
uv run superset-cli charts data prod 10 --json
uv run superset-cli charts data prod 10 --csv
uv run superset-cli annotation-layers list prod --json
uv run superset-cli annotation-layers get prod 50 --json
uv run superset-cli css-templates list prod --json
uv run superset-cli css-templates get prod 1 --json
uv run superset-cli themes list prod --json
uv run superset-cli themes get prod 1 --json
uv run superset-cli tags list prod --json
uv run superset-cli tags get prod 1 --json
uv run superset-cli reports list prod --json
uv run superset-cli reports get prod 1 --json
uv run superset-cli saved-queries list prod --json
uv run superset-cli saved-queries get prod 1 --json
uv run superset-cli queries list prod --json
uv run superset-cli queries get prod 1 --json
uv run superset-cli logs list prod --json
uv run superset-cli logs get prod 1 --json
uv run superset-cli logs recent-activity prod --json
uv run superset-cli permalinks resolve prod dashboard abc123 --json
uv run superset-cli datasources column-values prod table 21 country --json
uv run superset-cli security roles list prod --search Analyst --json
uv run superset-cli security roles get prod 7 --json
uv run superset-cli security users list prod --search reader --json
uv run superset-cli security users get prod 7 --json
uv run superset-cli security rls list prod --json
uv run superset-cli security rls get prod 7 --json
uv run superset-cli explore show prod --slice-id 10 --json
uv run superset-cli explore form-data prod example-key --json
```

Security reads obey server permissions; user endpoints may require server-side
`FAB_ADD_SECURITY_API`. Human output is limited to ID/name or username; user JSON
may contain personal metadata. Explore commands inspect saved state only, without
executing a query or creating an exploration.

### Chart data output

`charts data` exits 1 when every query fails or no successful query returns rows.
A successful scalar row (including zero or NULL) remains valid. Mixed results
succeed when at least one successful query has rows. With `--json`, the unchanged
raw payload is still printed to stdout on failure; a short diagnostic goes to stderr.

`--csv` emits column headers from `colnames` and one CSV table per query, separated
by a blank line. Numeric `__timestamp` values become ISO-8601 UTC timestamps;
other numeric columns remain unchanged. It cannot be combined with `--json`.

`--time-range` replaces the time range on every saved query. Repeatable
`--filter col=value` appends string equality filters to every query, preserving
existing filters. Values may contain `=`; empty columns/values are rejected.
These options execute a copied query context through the chart-data POST API
with CSRF handling; they do not save chart changes. Without overrides, the
original saved-chart GET endpoint is used. The chart must have a usable saved
`query_context` (save it in Explore first if missing).

```bash
uv run superset-cli charts data prod 10 --time-range '2026-04-01 : 2026-05-01' --filter region=west --json
```

### Chart cache controls

```bash
uv run superset-cli charts data prod 10 --cache-info
uv run superset-cli charts data prod 10 --force --allow-write --json
uv run superset-cli charts data prod 10 --time-range 'Last week' --filter region=west --force --allow-write --csv
uv run superset-cli cache invalidate prod --dataset 21 --dataset 22 --allow-write --json
```

Use discovered numeric IDs; these examples do not authorize live writes.
`--cache-info` reports each query's server-supplied cache hit/miss, key, timestamp,
and timeout without extra requests. Missing metadata is unknown, null stays null,
false means a miss, zero stays zero, and -1 denotes disabled caching. JSON and CSV
remain unchanged, including errors/empty-result exits. Different native-filter
combinations can have different cache keys; HTTP success is not freshness proof.

`--force` loads the exact requested queries from source and normally replaces
those cache entries, unless caching is disabled. It does not update saved chart
configuration or invalidate every dataset/filter combination. Saved-chart GET
uses `force=true`; copied override POST uses top-level boolean `force`. Because
force refresh deliberately changes cached state, it requires literal
`--allow-write` before auth/network access. Ordinary chart reads and non-force
query overrides retain their existing behavior. Source-verified on Superset 6.1.0;
unsupported endpoints/contexts fail rather than inventing another transport.

`cache invalidate` requires at least one positive numeric SQLA dataset ID; repeat
`--dataset`, duplicates are removed. UUIDs and implicit all-dataset targets are
not supported. IDs map to `<ID>__table` datasource UIDs, not dataset UUIDs. The
target OpenAPI must support `POST /api/v1/cachekey/invalidate` with string
`datasource_uids`; configured auth, CSRF, and server `CacheRestApi` invalidate
permissions apply. No service users, keys, or configuration are created.

**External prerequisites:** `STORE_CACHE_KEYS_IN_METADATA_DB=True`, tracked keys,
and compatible cache/data-cache backend, database, and key-prefix configuration.
Existing untracked entries are not indexed retroactively. Superset 6.1.0 deletes
through `cache_manager.cache` while chart results use `data_cache`; an incompatible
setup can remove tracking metadata and return 201 without evicting chart results.
The endpoint can also log incomplete deletion yet return success. JSON therefore
reports `{dataset_ids, datasource_uids, accepted, eviction_verified, response}`,
with `eviction_verified=false`, never invented deletion counts. Human output says
request accepted, **not verified eviction**.

A network failure leaves the outcome unknown; inspect server state before an
explicit rerun. Sent invalidations never replay automatically. Even a retry's
success cannot prove eviction after tracking records disappeared. Live acceptance
requires an explicitly authorized isolated instance: pre-cache multiple filter
combinations plus an unrelated dataset, invalidate only targets, and verify normal
non-forced rendered requests stop reusing old target results while unrelated
cache/session/Celery state stays intact. That live check has not been run. No
Redis flush or fallback is provided. See [ADR 0024](docs/decisions/0024-targeted-cache-controls.md).

### Read-only ZIP exports

```bash
uv run superset-cli dashboards export prod 7 8 --output dashboards.zip
uv run superset-cli charts export prod 10 --output charts.zip
uv run superset-cli datasets export prod 21 --output datasets.zip
uv run superset-cli databases export prod 1 --output databases.zip
```

Exports require positive integer IDs and a ZIP response. Existing output files
are refused unless `--force` is supplied; use a new destination to preserve an
older archive. Export files may contain sensitive connection or asset metadata.
There is no `--json` export mode and no server mutation.

### Chart and dashboard owners

These commands use legacy integer **user owner IDs**, verified against Superset 6.0 source. Inspect the target's capabilities; newer editor/viewer subject IDs are not interchangeable. Owners are independent of creators, last modifiers, viewers, dashboard roles, and ownership of related charts/datasets.

```bash
uv run superset-cli dashboards owners prod example-dashboard --json
uv run superset-cli charts owners prod 7 --json
uv run superset-cli dashboards owner-candidates prod --search Reader --page 0 --page-size 20 --json
uv run superset-cli charts owner-candidates prod --search Reader --json
uv run superset-cli dashboards owners-set prod example-dashboard --owner-id 2 --owner-id 3 --allow-write
uv run superset-cli charts owners-add prod 7 --owner-id 3 --allow-write --json
uv run superset-cli dashboards owners-remove prod 7 --owner-id 3 --allow-write
uv run superset-cli charts owners-set prod 7 --clear --allow-write
uv run superset-cli dashboards owners-remove prod 7 --owner-id 2 --clear --allow-write
```

Both groups provide `owners`, `owner-candidates`, `owners-set`, `owners-add`, and `owners-remove`. Chart UUIDs and dashboard slugs resolve through details to a numeric primary key before writes. Candidate discovery preserves the permission-filtered `count`/`result` envelope and searches names/usernames using the server's related-field `filter`; it does not require the security user directory. Missing or unsupported owner fields are errors, not empty lists.

Every owner mutation, **including no-ops**, requires literal `--allow-write` before any API request. IDs must be positive integers; repeat `--owner-id`, duplicates are removed, and display names are never resolved automatically. Replacement requires either IDs or `--clear`, not both. Removal of the last owner requires `--clear`; clear intent does not override server permissions. Already-present adds, absent removals, and unchanged replacements send no PUT.

Before writing, the target OpenAPI must document an integer `owners` array in the resource's PUT schema; unsupported/unavailable schemas fail closed. Only `owners` is submitted, with existing CSRF transport and no query-context clearing. Superset can retain a non-admin caller omitted from the requested list. Each sent update is read back: a requested transfer or self-removal is not reported as successful if effective owners differ. Add/remove is **non-atomic read-modify-write** and can overwrite concurrent owner edits; no unverified ETag support or atomicity is claimed.

Inspection JSON is `{"resource":"chart","id":7,"owners":[...]}`. Mutation JSON adds `operation`, `requested_owner_ids`, `write_performed`, `verified`, `matches_requested`, and `warning`. `write_performed` is `false` for a no-op, `true` after successful PUT, or `null` for an uncertain network outcome. If read-back fails, `owners` and `matches_requested` are `null` and `verified` is `false`. A mismatch, failed read-back, or unknown outcome emits evidence then exits **1**; inspect effective owners before retrying. No mutation is automatically retried. Existing `get --json` and generic `update --json` are unchanged. See [ADR 0020](docs/decisions/0020-guarded-resource-owners.md).

## Write commands

Every command in the table below requires `--allow-write` on every invocation. Without it the command prints what it *would* do and exits non-zero (dry-run by default).

```bash
# Charts
uv run superset-cli charts create     prod --body '{"slice_name":"Revenue","viz_type":"line"}' --allow-write
uv run superset-cli charts update     prod 42 --body '{"slice_name":"Revenue v2"}' --allow-write
uv run superset-cli charts update     prod 42 --clear-query-context --allow-write   # drop stale saved query_context after a params edit
uv run superset-cli charts delete     prod 42 --allow-write
uv run superset-cli charts favorite   prod 42 --allow-write
uv run superset-cli charts unfavorite prod 42 --allow-write

# Dashboards
uv run superset-cli dashboards create     prod --file dashboard.json --allow-write
uv run superset-cli dashboards update     prod 7  --body '{"published":true}' --allow-write
uv run superset-cli dashboards delete     prod 7  --allow-write
uv run superset-cli dashboards favorite   prod 7  --allow-write
uv run superset-cli dashboards unfavorite prod 7  --allow-write
uv run superset-cli dashboards copy       prod 7  --body '{"dashboard_title":"Revenue (copy)"}' --allow-write

# Datasets
uv run superset-cli datasets create  prod --file dataset.json --allow-write
uv run superset-cli datasets update  prod 21 --body '{"description":"updated"}' --allow-write
uv run superset-cli datasets delete  prod 21 --allow-write
uv run superset-cli datasets refresh prod 21 --allow-write

# Databases
uv run superset-cli databases create          prod --file database.json --allow-write
uv run superset-cli databases update          prod 1 --body '{"expose_in_sqllab":true}' --allow-write
uv run superset-cli databases delete          prod 1 --allow-write
uv run superset-cli databases test-connection prod --file connection.json --allow-write

# Saved queries
uv run superset-cli saved-queries create prod --body '{"label":"q1","sql":"select 1"}' --allow-write
uv run superset-cli saved-queries update prod 9 --body '{"label":"q1-v2"}' --allow-write
uv run superset-cli saved-queries delete prod 9 --allow-write

# SQL Lab
uv run superset-cli sqllab execute    prod --body '{"database_id":1,"sql":"select 1"}' --allow-write
uv run superset-cli sqllab format-sql prod --body '{"sql":"select 1"}' --allow-write
uv run superset-cli sqllab estimate   prod --body '{"database_id":1,"sql":"select 1"}' --allow-write
uv run superset-cli sqllab stop-query prod --body '{"client_id":"abc"}' --allow-write

# Tags, themes
uv run superset-cli tags create   prod --body '{"name":"finance"}' --allow-write
uv run superset-cli tags update   prod 1 --body '{"name":"finance-v2"}' --allow-write
uv run superset-cli tags delete   prod 1 --allow-write
uv run superset-cli themes create prod --body '{"theme_name":"Dark"}' --allow-write
uv run superset-cli themes update prod 1 --body '{"theme_name":"Dark v2"}' --allow-write
uv run superset-cli themes delete prod 1 --allow-write

# Security: roles, users, RLS rules
uv run superset-cli security role-create prod --body '{"name":"Analyst"}' --allow-write
uv run superset-cli security role-update prod 5 --body '{"name":"Analyst v2"}' --allow-write
uv run superset-cli security role-delete prod 5 --allow-write
uv run superset-cli security user-create prod --file user.json --allow-write
uv run superset-cli security user-update prod 2 --body '{"active":false}' --allow-write
uv run superset-cli security user-delete prod 2 --allow-write
uv run superset-cli security rls create  prod --file rls.json --allow-write
uv run superset-cli security rls update  prod 3 --body '{"name":"updated"}' --allow-write
uv run superset-cli security rls delete  prod 3 --allow-write

# Asset import (server-side multipart upload)
uv run superset-cli import upload prod dashboard --file bundle.zip --allow-write
uv run superset-cli import upload prod chart     --file bundle.zip --overwrite --passwords '{"db.zip":"hunter2"}' --allow-write
```

Both `--body '<json>'` and `--file <path-to-json>` accept the request payload. Pass `--body -` to read JSON from stdin. The two flags are mutually exclusive.

## Troubleshooting API failures

Generic HTTP failures print method, instance-relative path, status, and bounded,
redacted server details to stderr. Successful JSON stdout is unchanged. HTML
error pages are summarized rather than echoed; use server logs for their details.
Treat diagnostics as sensitive when sharing them.

Use the evidence, not identical retries: a 400 mentioning CSRF requires checking
auth/CSRF handling; validation errors require correcting the supplied fields.
A 403 is a permission failure, not proof that login expired. Authentication and
not-found errors retain their existing handling. No sent mutation is retried
automatically. If output is insufficient, inspect the live OpenAPI specification
and authorized server logs rather than extracting cookies into another client.

## Authenticated API escape hatch

After one capability check (`api --help`), prefer `api` for supported REST paths
that lack a named command, rather than writing an ad-hoc cookie/CSRF client.
Paths must stay under `/api/v1/` on the configured instance; no absolute URLs,
redirect following, traversal, or cookie values copied into another tool.

```bash
uv run superset-cli api prod /api/v1/dashboard/7
uv run superset-cli api prod /api/v1/_openapi --json
uv run superset-cli api prod /api/v1/dashboard/ --param 'q=(page:0,page_size:10)' --json
uv run superset-cli api prod /api/v1/dashboard/7 --method PUT --body '{"dashboard_title":"Example"}' --allow-write
```

Repeat `--param KEY=VALUE` for more parameters. Duplicate keys stay repeated on
the wire; select keys/encoding from the live schema, not guessed conventions.
All non-GET methods require literal per-invocation `--allow-write`. The wrapper
fetches CSRF automatically. Missing/rejected saved auth gets one announced,
validated cookie-import attempt; it does not launch a browser. Import must
validate `/api/v1/me/` before persisting state. If the loader exposes no usable
cookie, switch to an accessible supported-browser session or report blocked. Network failures and 403 are not login-expiry evidence. A sent
mutation is never replayed: inspect the instance before explicitly rerunning it.
A stale cookie and no cookie exposed by the loader are different outcomes; stop
repeat login/restart loops when the browser state is inaccessible. Prefer an
accessible supported-browser session, or report blocked.

Dashboard/theme/CSS diagnostics may inspect fields with GET without write
permission. Temporary changes still require explicit operator authorization,
`--allow-write` on every call, an original-value backup, and restoration. This
recipe does not grant that authorization. Confirm relevant calls and schema
against the live OpenAPI specification when version-specific behavior matters.

## Optional browser render verification

Core login/API use does not require Playwright. For an already authenticated
browser-render check, export a **new** private state file without changing the
CLI state. Cookie units are explicit, not guessed from their magnitude:
`browser-cookie3` 0.20.1's Chromium/Firefox/Safari loaders use Unix **seconds**;
its Firefox sessionstore extraction has absent expiry. For any other source,
verify its convention before choosing `seconds` or `milliseconds`. Absent,
zero, and negative session expiry become Playwright's `-1`. Malformed expiry
fails before output; secure/httpOnly/sameSite attributes are retained when
available. The exporter does not access browser databases or renew auth.

```bash
work=$(mktemp -d /tmp/superset-render.XXXXXX)
uv run superset-cli auth export-playwright prod --output "$work/state.json" --expiry-unit seconds
uv run --with playwright python scripts/verify_dashboard.py --help
```

The helper requires `--instance`, `--dashboard`, `--state`, and repeatable
`--expect` content selectors. From this checkout, invoke it with the exported
state and an installed browser. For example, set `CHROME` to the verified local
browser executable and use the dashboard's inspected rendered-content selector
(the following array syntax works in Bash/Zsh):

```bash
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
args=(--instance prod --dashboard 7 --state "$work/state.json")
args+=(--expect '[data-test-chart-id="10"] canvas' --browser-executable "$CHROME")
uv run --with playwright python scripts/verify_dashboard.py "${args[@]}"
```

Replace the example IDs/selector with discovered target values: a chart wrapper
or arbitrary nonempty HTML is not render evidence. `--tab NAME` paired with
`--tab-expect SELECTOR` validates a second representative tab; `--min-tabs` checks
the discovered tab count. `--screenshot-dir` captures each verified view at the
requested viewport; `--screenshot-selector` captures an inner dashboard container
instead. The JSON summary contains bounded console/page-error counts, not their
potentially sensitive text. HTTP 200 or a screenshot alone never counts as
verified: login, blank/hidden chart output, loading timeout, explicit chart error,
or page error exit nonzero. Treat such results as failed/blocked, not success.
Checks cover DOM text, nonempty SVG geometry, and nontransparent 2D-canvas
pixels, including native opacity/content-visibility checks and scrolling the
selected content into view. Unsupported or tainted canvases are blocked. This is
not a visual-regression or query-semantics oracle: inspect screenshots for color
contrast/occlusion and compare with a known-good reference at the same viewport.
State and screenshots can be sensitive; keep them out of git and remove the
private temporary directory after inspection. Synthetic Chrome tests validate
this recipe, not any real instance's current render or authentication.

## Local Superset for testing

`devenv` includes a process that boots a sqlite-backed Apache Superset on `http://localhost:8088` for ad-hoc CLI testing. No Redis, no Celery, no Docker. First boot installs Superset into `.devenv/state/superset/venv/` and seeds an admin user (~1–2 min). Subsequent boots are seconds.

```bash
devenv up superset                # start it (or: bash scripts/dev-superset.sh)
superset-open                     # open http://localhost:8088/login/ in your default browser
# log in as user: admin   password: admin

superset-cli instances add local http://localhost:8088
superset-cli auth login local     # reads cookies from your installed browser
superset-cli me show local --json
superset-cli tags create local --body '{"name":"smoke"}' --allow-write --json
```

The dev instance disables CSRF and Talisman so cookie auth works without extra setup. It is not safe to expose. State lives under `.devenv/state/superset/`; delete that directory to reset.

### Snowflake connections from `~/.snowflake/connections.toml`

On every Superset start, `scripts/dev-superset-import-snowflake.sh` reconciles the local instance's database list against `~/.snowflake/connections.toml`. Connections missing in Superset are created as `snowflake-<name>`; existing ones are skipped. Auth methods supported:

- **password** — baked into the SQLAlchemy URI.
- **key-pair** (`private_key_path` / `private_key_file`) — mapped to `authenticator=snowflake_jwt`, key path stored in the database's `extra`.
- **PROGRAMMATIC_ACCESS_TOKEN** — the file at `token_file_path` is read and submitted as the password. No `authenticator` parameter is sent (the connector rejects `PROGRAMMATIC_ACCESS_TOKEN` as an authenticator value even though the Snowflake CLI uses that label in TOML).
- **externalbrowser / oauth** — skipped (no browser on the server).

If a TOML entry has no `database` field, the importer defaults to `SNOWFLAKE_SAMPLE_DATA` so Superset's connection-test query has a current database. Failures in the importer never bring down the Superset server. Secrets written into Superset's sqlite metadata DB are protected only by a static dev `SECRET_KEY` — do not point this at a production credential.
