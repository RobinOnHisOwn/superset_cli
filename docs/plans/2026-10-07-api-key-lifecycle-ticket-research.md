# Research API-key lifecycle and create scoped follow-up tickets

**Date:** 2026-10-07

## Goal

Turn the missing service-account key lifecycle, secret delivery, and caller safeguards into evidence-backed tickets without implementation or live mutations.

## Planned changes

1. Check existing tickets and ADRs 0006, 0009, 0023, and 0024 for duplicates and scope boundaries.
2. Inspect pinned FAB 5.2.2 and Superset 6.1.0 source, official 1Password documentation, local non-authenticated CLI help, and current client/command entry points.
3. Create five linked todo tickets covering the backend integration decision, lifecycle commands, safe issuance, caller allowlist, and deployment role acceptance.
4. Validate relative documentation links and ticket metadata; record unknown deployment prerequisites rather than guess them.

## Findings and assumptions

- Verified from pinned source: FAB API-key endpoints operate on the authenticated user; create accepts name, scopes, and expires_on, not a target user. Get/revoke return 404 for another user's key.
- Verified: FAB's SQLA manager accepts an explicit user for internal issuance and a UUID for revocation. These internal methods are not an authorized cross-user HTTP interface.
- Verified: FAB key validation checks hashes, key activity/expiry, and user activity, but does not enforce the stored scopes string. Do not treat scopes as dataset isolation.
- Verified: the revoke endpoint ignores the manager's boolean result; HTTP 200 alone is not proof of revocation.
- Verified: installed 1Password CLI 2.33.1 supports item JSON via stdin (`op item create -`). Official docs warn against secrets in assignment arguments. No vault access or issuance was tested.
- Verified: the CLI reads credentials in SupersetClient construction. Dataset rejection must occur before `_require_storage_state` and `_client`, not just before the POST.
- Verified from source: the existing invalidation/CSRF/current-user/OpenAPI flow requires the four specified permission pairs. Runtime deployment registration, inherited role grants, and cache eviction remain unknown.
- Proposed: authorized deployment-side provisioning adapter, verified read-back and compensating revocation, and an allowlist in the owning caller. Ticket creation does not approve a backend design, CLI contract, dependency, or default change.
- Unknown: available deployment integration, target backend configuration, provisioning identity, 1Password account/vault permissions, and ambiguous-outcome recovery facilities.

## Verification

- Research only: pinned upstream source downloads and local `op --version`, `op item create --help`, `op item get --help`; no authenticated 1Password or Superset calls.
- From the worktree cwd, `direnv exec "$PWD" uv run pytest tests/test_docs_links.py -q`: **2 passed** (includes all new relative links).
- `git diff --check`: passed. A Python metadata check verified all five `Status: todo` fields and the plan's final decision-follow-up section.
- `specdocs_validate`: reported an existing `docs/architecture/README.md` filename-pattern error in the tool's current workspace; it did not provide targeted validation of this worktree plan. The plan follows the repository template, not the tool's `plan-*.md` naming convention.
- Application tests/build are not required for documentation-only changes; no application behavior changes.

## Decision follow-up

No durable decision change.

Future implementation must review ADR 0023's no-issuance/revocation boundary and record the selected provisioning trust boundary, secret-delivery contract, and caller policy in the owning repositories. The tickets identify those follow-ups without accepting a design here.
