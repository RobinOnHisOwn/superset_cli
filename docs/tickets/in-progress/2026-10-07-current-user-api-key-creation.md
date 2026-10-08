# Create current-user API keys with verified 1Password delivery

- Status: in-progress
- Implementation: local guarded CLI, captured 1Password adapter, original-caller reconciliation/rollback and regression tests implemented. See [plan](../../plans/2026-10-07-current-user-key-creation.md).
- Acceptance gate: no authorized disposable vault/Superset target supplied; live delivery and key rejection remain unverified. Do not close or release based on mocks alone.
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: [lifecycle](../in-progress/2026-10-07-api-key-lifecycle.md), [service-user issuance](../todo/2026-10-07-secret-safe-key-issuance.md), [backend integration](../todo/2026-10-07-service-key-provisioning-integration.md), [ADR 0023](../../decisions/0023-environment-bound-api-keys.md)

## Context

Split the remaining current-user create command from the lifecycle ticket. Native FAB creates for the authenticated caller, not an arbitrary service user; that narrower workflow does not require a cross-user backend adapter. Service-account deployment/provisioning remains separate.

## Selected scope

`auth api-key create INSTANCE --name NAME --expires-on ISO --operation-id UUID --server-timezone IANA --op-account ACCOUNT --op-vault VAULT --allow-write [--json]`

No plaintext output/file sink, cross-user targeting, rotation, or automatic creation retry. Use a dedicated API Credential item, create/read/edit a non-secret placeholder before key issuance to verify destination permissions, then deliver via captured stdin JSON and verify item/key metadata and secret read-back. The existing caller credential survives revocation of the new key. Require list/create/get/revoke permissions before issuance and a unique operator-supplied operation UUID for lost-response reconciliation.

## Definition of done

- [x] Plan and source-verified native Superset/FAB and installed 1Password contracts.
- [x] Failing tests before implementation; callback write guard before credentials, subprocesses or network. Optional-instance parsing may read non-secret config before the callback.
- [x] Validate name, UUID, explicit destination and future timezone-aware expiry before access.
- [x] Verify caller lifecycle permissions and destination create/read/edit capabilities before issuance.
- [x] Deliver only through stdin JSON; capture subprocess output; expose only UUID/operation/item/vault identifiers and stored-state results.
- [x] Reconcile lost create responses by operation marker, never blindly replay POST; compensate delivery failures using the surviving caller and verify revocation. Explicitly report unknown cleanup.
- [x] Test dummy-secret leak sentinels, HTTP/process failures, malformed responses, timeouts, interruptions, expiry, missing guard, existing operation and no mutation replay.
- [x] Update README, architecture and decisions; 91 focused tests and 1,085 full tests passed on both supported Python versions (13 skipped each); color/no-color help, manual no-write guard smoke, build and isolated wheel/sdist help checks passed. See plan for evidence and remaining CI/live gates.
- [ ] Before release, authorized disposable-vault/Superset end-to-end acceptance. Do not claim local mocks prove live delivery or key rejection.

## Decision follow-up

Decision record update required: current-user secret-delivery, preflight, expiry and recovery contract in `docs/decisions/0025-current-user-api-key-creation.md`; revise ADR 0023's no-issuance boundary.
