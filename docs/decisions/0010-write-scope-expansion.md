# 0010: Write-scope expansion

- Status: accepted
- Date: 2026-06-06
- Supersedes: [`0001-read-only-bootstrap-scope`](0001-read-only-bootstrap-scope.md)
- Related: [`0009-write-command-explicit-opt-in`](0009-write-command-explicit-opt-in.md), `docs/plans/2026-06-06-write-command-rollout.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

The product started read-only (ADR 0001) so the bootstrap could establish packaging, configuration, auth, and stable read APIs without write-side risk. The read surface is now broad and the CLI patterns are stable. Users now need write capability to actually manage Superset content from automation.

ADR 0009 already locked in the contract that *any* write command requires `--allow-write` on every invocation. What was missing was an explicit scope decision about *which* writes are in.

## Decision

Expand the product scope from read-only to "read by default, write opt-in." The CLI may now perform Superset write operations against the approved surface below. Read commands remain unchanged and require no flag.

### Approved write surface (initial)

- **charts**: create, update, delete, favorite, unfavorite.
- **dashboards**: create, update, delete, favorite, unfavorite, copy.
- **datasets**: create, update, delete, refresh.
- **cache controls** (2026-10-07): targeted dataset cache invalidation and explicit chart-result force refresh; see [ADR 0024](0024-targeted-cache-controls.md). No global backend deletion or deployment changes.
- **databases**: create, update, delete, test-connection.
- **saved-queries**: create, update, delete.
- **sqllab**: execute, format-sql, estimate, stop-query.
- **tags**: create, update, delete.
- **themes**: create, update, delete.
- **security**: roles create/update/delete; users create/update/delete; RLS rules create/update/delete.
- **current-user API keys** (2026-10-07): guarded create with verified 1Password delivery and revoke; see [ADR 0023](0023-environment-bound-api-keys.md) and [ADR 0025](0025-current-user-api-key-creation.md). No cross-user provisioning or server enablement.
- **import**: dashboard, chart, dataset, database, saved-query bundles via multipart upload.

### Safety contract

- Every write command requires the literal `--allow-write` flag on every invocation (per ADR 0009). No prompts, no env var, no config flag, no parent-command grant.
- Without the flag the command exits non-zero with a message naming the would-be mutation and the missing flag.
- The check is centralised in a shared `cli.py` helper so no write command can forget it.
- Help text for every write command states: *"Required to actually perform the write. Without it the command is a dry-run."*
- Sensitive security/admin writes (roles, users, RLS) use the same `--allow-write` policy. No softer or harder bar — uniform friction.

### Out of scope (deliberately deferred)

- Asset-bundle exotic endpoints (warm-up, cache-screenshot, embedded-config update, certified-by helpers). Open a per-resource ticket if a user needs them.
- Database driver upload, parameter validation, SQL validation. Same — open tickets when needed.
- Dashboard embedded-config write. Same.

## Consequences

Positive:

- Product is no longer constrained to read-only. The nine write-command tickets are unblocked.
- Surface is enumerated explicitly, so future agents and humans can tell whether a new endpoint falls inside or outside the approved scope without re-litigating it.
- `--allow-write` is the single visible safety primitive at every write surface — easy to grep, hard to accidentally satisfy.

Negative / honest caveats:

- The CLI is no longer trivially safe in production by virtue of being read-only. Operators must understand that running a write command without `--allow-write` is the only thing that keeps a destructive action from happening.
- "Read by default, write opt-in" is a more nuanced posture than "read-only." Documentation, help text, and onboarding need to keep this distinction visible.
- Future write tickets that fall outside this approved surface still require their own scope decision before landing.

## Alternatives considered

- **Stay read-only.** Rejected: users have explicit need for write automation, and ADR 0009 already provides the safety mechanism that makes opt-in writes safe.
- **Allow *all* Superset write endpoints, not just the listed surface.** Rejected: the CLI gains coverage gradually with deliberate UX choices per command. Opening every endpoint at once invites copy-paste of Superset shapes the CLI hasn't actually validated.
- **Use a per-command confirmation prompt instead of (or in addition to) `--allow-write`.** Rejected by ADR 0009. Repeated here for completeness.
- **Promote `--allow-write` to a config-file or env-var opt-in for power users.** Rejected by ADR 0009. Repeated here for completeness.
