# 0025: Current-user key creation with verified 1Password delivery

- Status: accepted
- Date: 2026-10-07
- Related: [plan](../plans/2026-10-07-current-user-key-creation.md), [ticket](../tickets/in-progress/2026-10-07-current-user-api-key-creation.md), [authentication](0023-environment-bound-api-keys.md), [write guard](0009-write-command-explicit-opt-in.md), `src/superset_cli/key_issuance.py`, `tests/test_api_key_creation.py`

## Context

The user explicitly requested API-key creation. Native FAB 5.2.2 creates for the authenticated user and returns plaintext once. That current-user workflow is distinct from cross-user service provisioning, which still requires an authorized backend integration. Issued keys must not appear in terminal output, files, shell history or process arguments. HTTP or subprocess success alone does not establish safe delivery.

## Decision

Expose `auth api-key create` only with explicit name, operation UUID, expiry, verified server clock timezone and 1Password account/vault. The callback checks literal `--allow-write` before credential access, processes and network; optional-instance parsing may read non-secret configuration before the callback. Require HTTPS except loopback HTTP before loading caller credentials. Disable automatic redirects on shared non-GET transport so POST/PUT/DELETE remain single-send. No new dependencies, cross-user target, plaintext sink, rotation, stored scope authorization, or automatic mutation retry.

Require active identified caller metadata and the four `ApiKey` grants (`can_list/create/get/revoke`) plus CSRF read permission from source-verified `/me/roles/`. Native list supplies the before-image and rejects an existing operation suffix. The original caller authenticates creation, verification and rollback; it is never replaced by the newly minted key. This is independent of the new key, not a promise that the original credential cannot expire or lose permissions.

Initially support the locally inspected `op` 2.33.1 contract. Use an explicit account and resolve the vault to its immutable ID. Create a dedicated API Credential placeholder item, verify correlation/destination and read access, edit the non-secret placeholder, then verify edit access before issuing a key. Never overwrite an existing item. After issuance, write only through captured stdin JSON to the known item/vault IDs. Read with `--reveal --format json --cache=false`; compare the credential in memory and verify concealed field type, operation, UUID, owner and instance URL. Filter subprocess environment to required OS/1Password settings and exclude caller bearer/cookie values even when aliased under allowed variable names. Never forward captured output or exception bodies.

Require timezone-aware input expiry in the future and within 90 days. FAB's model stores naive `DateTime` and compares it with `datetime.now()`. Convert the input instant to the operator-verified server local-clock IANA timezone and send naive wall time; read back the same naive expiry. Reject DST folds that native storage cannot represent. Do not infer server timezone from deployment names, UTC conventions or the caller's clock.

On failure or a caught interruption after attempting POST, discover the new key from the exact operation-marked name and before-image if the response UUID was lost. Revoke with the original caller and require existing stored-state read-back verification. Missing/multiple matches, late creates and failed cleanup remain explicitly unverified. Do not resend POST or item-create. Confirmed placeholder/item cleanup is best-effort; report deletion as requested, never atomic or proven. Retain only non-secret recovery identifiers in command output.

## Consequences

Success means verified stored key identity/expiry and 1Password read-back, not observed authentication using the new key. JSON contains operation/key/item/vault IDs, stored status, revocation status, outcome and item-cleanup status; conventional argument/config/auth errors keep existing CLI handling. No plaintext key/hash is returned. Existing local auth bindings are unchanged; existing JWT transport may still refresh its own auth state.

Operation-marked names are correlation, not backend idempotency or uniqueness constraints. Never reuse an operation UUID concurrently or blindly rerun after ambiguity. A timed-out request can complete after the reconciliation read. Operators must inspect Superset metadata and the dedicated 1Password operation marker before deciding recovery; if independent cross-user or crash-safe recovery is required, use the separate deployment integration rather than extending this native path.

No atomic transaction spans Superset and 1Password. Uncatchable termination can prevent compensation, and Python does not guarantee memory zeroization. Existing credentials, backend timezone, installed version and destination permissions are deployment prerequisites. End-to-end release acceptance with an authorized disposable vault and Superset target remains unverified; local adapters and help/template inspection are not substitutes.

## Alternatives considered

### Return the key in stdout or a private file

Simpler, but violates the repository's no-secret-output issuance contract and puts secret lifecycle management on every caller.

### Wait for a cross-user backend adapter for all creation

Required for service-user targeting and stronger reconciliation, but unnecessary for the narrower authenticated-current-user path. Preserve that separate ticket rather than invent an impersonation flag.

### Issue before checking destination write access

Avoids the placeholder edit, but knowingly creates usable credentials when vault permissions are missing. A dedicated placeholder is the smallest way to check create/read/edit permissions without issuing a key.
