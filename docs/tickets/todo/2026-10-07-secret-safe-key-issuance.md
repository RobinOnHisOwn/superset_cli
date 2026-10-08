# Deliver newly issued keys directly to 1Password with failure revocation

- Status: todo
- Blocker review (2026-10-07): backend independent revocation/reconciliation remains unknown; no verified destination account/vault or authorized disposable end-to-end test was supplied. Do not issue a key until these prerequisites are verified. Metadata/revoke CLI work does not establish a cross-user recovery integration. See [review plan](../../plans/2026-10-07-open-key-todos.md).
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: [backend integration](2026-10-07-service-key-provisioning-integration.md), [lifecycle](../in-progress/2026-10-07-api-key-lifecycle.md), [ADR 0023](../../decisions/0023-environment-bound-api-keys.md), [research plan](../../plans/2026-10-07-api-key-lifecycle-ticket-research.md)

## Context

The narrower [current-user creation ticket](../in-progress/2026-10-07-current-user-api-key-creation.md) implements delivery and original-caller compensation using native endpoints. This service-user workflow still requires the authorized backend integration and its stronger recovery contract; local current-user tests do not close this ticket.

An issued plaintext key is returned once by FAB. Move it directly into 1Password without terminal output, plaintext files, shell history, or process arguments. Creation is incomplete until storage is verified. On failure, revoke and verify cleanup; do not leave an unreported usable key.

## Verified knowledge

- Official 1Password guidance warns that assignment arguments expose secrets to history/process inspection. JSON stdin is supported: installed `op` 2.33.1 help documents `op item create -`.
- A `CONCEALED` field identifies a secret, but concealment is not a substitute for capturing subprocess output. Never forward create/get output to the terminal, including JSON, dry-run previews, or error diagnostics.
- `op item get` accepts immutable item IDs and explicit vault selection; service accounts require vault specification. Read-back of the secret must be captured in memory with the appropriate reveal/field options verified against the chosen CLI version.
- FAB creation returns UUID plus plaintext. Native revocation is owner-scoped and its HTTP 200 is insufficient proof; the backend integration must support reliable compensating revocation for service users.
- Stdin prevents file/argument exposure, not privileged process-memory inspection. Python cannot promise reliable memory zeroization; do not claim it does.

## Proposed minimal approach

Use existing HTTP transport and Python stdlib subprocess support, with an argument list (no shell), private stdin containing the item JSON, and captured stdout/stderr. Verify the chosen CLI template/category and version before implementation; do not add an SDK dependency unless this verified path fails requirements.

Require explicit account/vault destination and a surviving provisioning/revocation identity. Prefer creating a dedicated item over overwriting an existing credential; rotation/replacement behavior is a separate contract to approve.

## Definition of done

- [ ] Resolve the backend contract and approve the destination/output/expiry contract. Preflight `op` availability/version, authentication, vault write/read permissions, and revocation capability before issuing a key.
- [ ] Require literal `--allow-write` before issuance or 1Password mutation. Dry-run must not issue, store, or print a prospective secret.
- [ ] Transfer the secret via stdin JSON only; prohibit key values in argv, environment propagation to unrelated child processes, files, HTTP/subprocess debug logs, exception text, and human/JSON output.
- [ ] Capture the returned immutable item/vault IDs; read the stored field through a captured pipe, compare in memory with the issued key, and check destination and key UUID metadata. Do not accept a successful create exit code alone.
- [ ] On create/read-back mismatch, failure, interruption, or timeout after issuance, attempt independently authenticated revocation and verify it. Retain only non-secret recovery identifiers.
- [ ] Model lost issuance responses and lost 1Password responses as ambiguous outcomes. Reconcile before retrying; do not blindly create a second key/item. Backend reconciliation is a prerequisite if the key UUID was lost.
- [ ] Report failed/unverifiable revocation explicitly with safe recovery metadata and non-zero exit; never claim atomicity across Superset and 1Password.
- [ ] Test using fake HTTP/subprocess adapters and a distinctive dummy secret: inspect stdout/stderr, exceptions, argv, temp-file writes, and all failure paths. Test subprocess timeouts, signals, malformed output, stored mismatch, and cleanup failures.
- [ ] Verify the exact stdin/create/read-back behavior with an explicitly authorized disposable vault and test backend before release; local help inspection is not end-to-end evidence.

## Sources

- [1Password create items](https://developer.1password.com/docs/cli/item-create/)
- [1Password item fields](https://developer.1password.com/docs/cli/item-fields/)
- [1Password item command reference](https://developer.1password.com/docs/cli/reference/management-commands/item/)
- [FAB key API](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/api_key/api.py)
- Local evidence: `op --version`, `op item create --help`, `op item get --help`; no vault or secret was accessed.

## Decision follow-up

Decision record update required: secret-delivery, subprocess-output, recovery and supported 1Password contract; implementation ownership depends on the selected backend integration.
