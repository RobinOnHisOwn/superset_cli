# Provide explicit pipeline-safe service-key secret output

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: [backend prerequisite](../in-progress/2026-10-07-service-key-provisioning-integration.md), [service identity](2026-10-07-minimal-cache-service-role.md), [acceptance](2026-10-08-service-account-isolated-acceptance.md), [ADR 0023](../../decisions/0023-environment-bound-api-keys.md)

## Context

An issued key is a one-time secret. Provide an explicit secret-output mode suitable for a shell pipeline in whichever supported CLI/operator issuance path the backend research establishes. Default human/JSON output and diagnostics remain secret-free. This replaces the earlier requirement for built-in 1Password delivery; storage and dataset allowlists belong in the shell/caller.

## Definition of done

- [ ] Resolve the backend integration/operator fallback first; do not issue a key without verified service identity, exact permissions, ownership checks, and independently authenticated revocation/reconciliation access.
- [ ] Agree and document the explicit output contract before implementation; write a plan and failing tests first. Preserve existing metadata JSON contracts.
- [ ] Require literal `--allow-write` for issuance. Secret output is a separate explicit opt-in, never implied by `--json` or write authorization.
- [ ] Make the explicit mode emit only the plaintext key to stdout, suitable for piping; send only secret-free metadata/diagnostics to stderr. Default output never includes the plaintext key or hash.
- [ ] Keep secrets out of command arguments, error bodies, exception messages, HTTP/debug logs, default human/JSON output, and temporary files. Do not add secret-value CLI arguments.
- [ ] Verify newly issued ownership before emitting the secret. Reject owner/role mismatches; document independently authorized recovery if issuance already occurred.
- [ ] Test with a distinctive dummy secret across success, error, timeout, malformed response, ownership mismatch, interruption, and broken-pipe paths; assert no leakage except the explicitly requested successful secret stream.
- [ ] Never automatically retry sent issuance/revocation. A lost response or failed delivery reports an uncertain outcome, non-zero exit, and safe reconciliation/revocation identifiers when known; do not claim downstream storage succeeded.
- [ ] Document shell pipeline usage and partial-delivery recovery without embedding real secrets. Integration-test only through the authorized isolated acceptance ticket.

## Notes

No 1Password subprocesses, vault management, automatic destination verification, or dataset-allowlist implementation. The shell/caller owns downstream secret handling and pipeline failure checks.
