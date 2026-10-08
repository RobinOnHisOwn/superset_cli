# Provision and verify the minimal cache service identity

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: [backend research](2026-10-07-service-key-provisioning-integration.md), [permission management](2026-10-08-security-role-permission-management.md), [secret output](2026-10-07-secret-safe-key-issuance.md), [acceptance](2026-10-08-service-account-isolated-acceptance.md), [ADR 0024](../../decisions/0024-targeted-cache-controls.md)

## Context

Provision `svc_cache_invalidator` with a dedicated role containing exactly these four permission/resource pairs:

| Permission | Resource | Purpose |
| --- | --- | --- |
| `can_invalidate` | `CacheRestApi` | Invalidate tracked cache entries |
| `can_read` | `SecurityRestApi` | Retrieve CSRF token |
| `can_read` | `CurrentUserRestApi` | CLI authentication validation |
| `can_get` | `OpenApi` | CLI invalidation schema preflight |

Reuse existing user/role CRUD. Runtime identity must not receive Admin, dataset/query access, administration, or API-key-management permissions. Provisioning and revocation use a separate privileged operator identity.

## Definition of done

- [ ] Write a short implementation plan and failing tests before any code change; consult ADRs 0009, 0023, and 0024.
- [ ] Inspect existing user/role command contracts and reuse them; add only capabilities identified by the permission-management ticket, not a parallel provisioning client.
- [ ] Verify exact service-user identity/activity, role identity, current grants, all effective direct/group/inherited roles, and any role synchronization before changing anything. Reject unexpected privilege drift rather than silently stripping or adopting it.
- [ ] Resolve permission IDs from target metadata; never guess IDs or infer grants from role names. Define and test the expected absent-resource bootstrap state separately from existing-resource drift.
- [ ] Require literal `--allow-write` for each remote mutation, using the shared guard before credentials/network access; test that missing opt-in sends no requests.
- [ ] Provision/assign exactly the four grants, then read back the role and effective user permissions. Unexpected grants or incomplete read-back are non-success.
- [ ] Issue the service-owned key only through the verified integration or documented operator fallback; verify returned/stored ownership is `svc_cache_invalidator`, not the administering human.
- [ ] Never automatically retry sent mutations. Report uncertain outcomes with non-secret identifiers and read-only reconciliation steps.
- [ ] Update relevant CLI docs/tests and record durable decisions if needed. Defer live execution to explicitly authorized isolated acceptance.

## Notes

Dataset allowlists are caller responsibilities; these permissions do not enforce a dataset allowlist. No 1Password integration is included. This ticket authorizes no production or other live mutations.
