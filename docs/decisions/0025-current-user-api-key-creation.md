# 0025: Current-user key creation with explicit pipeline output

- Status: accepted
- Date: 2026-10-08
- Related: [correction plan](../plans/2026-10-08-pr12-pipeline-issuance.md), [ticket](../tickets/in-progress/2026-10-07-current-user-api-key-creation.md), [authentication](0023-environment-bound-api-keys.md), [write guard](0009-write-command-explicit-opt-in.md), `src/superset_cli/key_issuance.py`, `tests/test_api_key_creation.py`

## Context

PR 11 replaced mandatory built-in 1Password delivery with caller-owned storage and separate explicit secret output. The initial PR 12 implementation followed the superseded requirement. Keep native current-user creation distinct from privileged service-user administration, which remains blocked on its own backend and independent recovery contract.

## Decision

Require literal `--allow-write` and separate `--secret-output` before callback credential/network access. Refuse issuance without the latter rather than discard the one-time value. Reject combining secret output with `--json`. Successful explicit output is exactly the key plus newline on stdout; secret-free metadata goes to stderr. Existing list/get/revoke JSON contracts and local bindings do not change. No secret-value arguments, files, environment exports, 1Password subprocesses or downstream verification.

Use existing native transport and owner-scoped list/get/revoke. Before POST require an active identified caller, four ApiKey lifecycle grants and CSRF read access, a before-image and no existing operation marker. After creation require a new UUID, valid key syntax, matching name/activity/expiry, successful owner-only native GET and unchanged active caller ID before emitting. Native schemas do not expose owner IDs: owner proof comes from the source-verified GET ownership check and caller identity. Do not invent cross-user targeting or permission inference from role names. Runtime identities receive no lifecycle grants.

Retain required future timezone-aware expiry within 90 days and an independently verified server IANA clock timezone. FAB stores naive DateTime and compares with local datetime.now(); convert to naive wall time, reject DST folds, recheck expiry before POST and verify exact stored expiry. Operator/deployment clock correctness is a prerequisite, not inferred from UTC conventions.

Never replay POST or revocation, including automatic redirects on shared non-GET transport. Reconcile a lost response by the exact operation-marked name and before-image, then compensate failures with the original caller and verified stored revocation. Missing/multiple matches, lost permissions, late completion and unavailable cleanup stay unverified. An operation UUID is correlation, not backend idempotency; never blindly regenerate or reuse one after ambiguity.

Write and flush inside the guarded operation. Short writes, broken pipes and caught interruptions cause non-success and attempted compensation; partial output may already have escaped. Prevent a repeated Python exit flush on a broken real stdout descriptor; do not restore SIGPIPE's default handler. Suppress raw exceptions and HTTP bodies. Preserve a completed emission record if client shutdown later fails rather than replay or reissue.

## Consequences

A successful flush proves only emission, not downstream receipt, storage or durability. The shell/caller owns storage and pipeline status checking; use pipefail and independently authorized recovery if a receiver fails after reading. Metadata fields are operation_id, key_uuid, owner_id, emitted, revocation_verified and outcome. Default invocations never emit a secret; conventional preflight errors remain secret-free and pipeline stdout stays empty.

No atomic transaction spans issuance and a caller pipeline. Uncatchable termination can prevent compensation; Python does not guarantee memory zeroization. Existing JWT transport may refresh its own auth state, but newly issued keys never replace it. No live authorized isolated target was supplied; release acceptance of ownership, expiration and rejection remains unverified.

## Alternatives considered

### Keep automatic 1Password delivery

Rejected by PR 11's current scope. It couples the CLI to a vendor and claims responsibility for storage that belongs to the caller.

### Let --json or --allow-write imply secret output

Rejected: either would silently change existing secret-free output expectations. Separate literal opt-ins are required.

### Issue a key without any output opt-in

Rejected: metadata alone cannot recover a one-time plaintext value; silently discarding it creates an unusable undisclosed credential.
