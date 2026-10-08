# Verify service-account administration on an authorized isolated instance

- Status: todo
- Priority: high
- Type: research
- Created by: agent
- Created at: 2026-10-08
- Related: [backend integration/fallback](2026-10-07-service-key-provisioning-integration.md), [permission management](2026-10-08-security-role-permission-management.md), [service identity](2026-10-07-minimal-cache-service-role.md), [secret output](2026-10-07-secret-safe-key-issuance.md), [cache acceptance](../in-progress/2026-10-07-targeted-cache-invalidation.md), [ADR 0023](../../decisions/0023-environment-bound-api-keys.md), [ADR 0024](../../decisions/0024-targeted-cache-controls.md)

## Context

Local tests do not establish live ownership or least privilege. After the implementation/fallback is ready, test only on an explicitly authorized isolated Superset instance, never production by default. Reuse existing cache acceptance work rather than creating a second cache implementation.

## Definition of done

- [ ] Obtain explicit target and mutation authorization; verify instance isolation, versions, key-storage/config prerequisites, recovery credentials, and disposable fixtures. Stop if these prerequisites are unknown.
- [ ] Before each mutation verify identity, role permissions, and existing key ownership as applicable; reject unexpected drift. Use literal `--allow-write` on every remote mutation invocation.
- [ ] Prove the issued key belongs to `svc_cache_invalidator`, not the administering human, using independently trusted backend metadata and runtime `/me/` authentication.
- [ ] Prove the dedicated role has exactly the four required pairs and the user's other effective grants do not broaden runtime privileges.
- [ ] Verify existing CLI API-key authentication, CSRF retrieval, OpenAPI invalidation preflight, and targeted cache invalidation with the service credential. Distinguish HTTP acceptance from actual cache eviction/freshness per existing cache acceptance requirements.
- [ ] Verify unauthorized dataset/data/query operations and administration/key-management operations fail with authorization denials on valid disposable fixtures, not merely missing-resource errors. If a negative probe could mutate, explicitly authorize it and supply literal `--allow-write`.
- [ ] Revoke through the separate operator integration/fallback without adding runtime key-management permissions; verify backend revoked state and rejection of the formerly usable credential.
- [ ] Verify default human/JSON output and error logs contain no plaintext key; verify only explicit secret-output mode produces the secret stream. Capture only redacted/non-secret evidence.
- [ ] Exercise mocked uncertain-outcome cases and confirm no automatic sent-mutation retries; document live reconciliation/cleanup, exact commands, actual results, and unverified conditions.
- [ ] Update linked tickets with evidence. Never report isolated acceptance as production verification.

## Notes

1Password and dataset allowlist implementation remain in the shell/caller. No credentials, real instance identifiers, or captured private data belong in this public repository.
