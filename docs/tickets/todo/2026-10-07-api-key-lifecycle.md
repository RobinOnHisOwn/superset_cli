# Add guarded API-key lifecycle commands

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Related: [backend prerequisite](2026-10-07-service-key-provisioning-integration.md), [safe issuance](2026-10-07-secret-safe-key-issuance.md), [ADR 0009](../../decisions/0009-write-command-explicit-opt-in.md), [ADR 0023](../../decisions/0023-environment-bound-api-keys.md), `src/superset_cli/cli.py`, `src/superset_cli/client.py`

## Context

`auth api-key set/clear` validates/manages a local environment binding; it does not create or revoke server keys. Add server lifecycle support without exposing issued secrets. Creation must ship with safe delivery, not an intermediate command that prints a key.

## Verified knowledge

FAB 5.2.2 uses permission resource `ApiKey` with `can_list`, `can_create`, `can_get`, and `can_revoke`, distinct from the four-permission cache runtime role.

| Operation | Endpoint | Result |
| --- | --- | --- |
| List | GET `/api/v1/security/api_keys/` | 200, `result` array for current user; no list pagination implemented here |
| Create | POST same path | 201, `result` with UUID and one-time plaintext `key` |
| Get | GET `/api/v1/security/api_keys/{uuid}` | 200 metadata; 404 for missing/foreign key |
| Revoke | DELETE same UUID path | 200 message; 404 for missing/foreign key |

Metadata fields are uuid, name, key_prefix, scopes, active, created_on, expires_on, revoked_on, last_used_on. Get/list omit plaintext. Stored `active` alone is not proof of effective validity; expiry/revocation and user activity also matter.

The revoke route ignores `sm.revoke_api_key`'s boolean result. Verify `active=false` and revocation metadata after deletion; surface unverifiable outcomes instead of treating HTTP 200 as proof. Revoking the caller's own credential may prevent read-back; require a surviving authorized credential or independent backend confirmation.

Reuse `_client`, `_require_allow_write`, and shared CSRF transport. Never retry a sent mutation automatically. FAB native endpoints cannot provision/revoke another user's keys, even for an admin.

## Definition of done

- [ ] Approve command names and human/JSON contracts; preserve local set/clear semantics. Write an implementation plan and failing tests first.
- [ ] Implement current-user list/get metadata and guarded revoke using verified endpoint schemas and permission names. Do not assume generic list pagination applies.
- [ ] Require literal `--allow-write` before credential loading/network access for create/revoke; include the existing dry-run help wording.
- [ ] Ship create only with the safe-issuance ticket's verified sink/recovery workflow. Human and JSON output must never contain plaintext keys.
- [ ] Do not add `--user` targeting to native endpoints. Cross-user support remains blocked on the authorized backend integration.
- [ ] Test current-user scope, foreign/missing UUIDs, malformed create/expiry, missing opt-in, 401/403/404/500, failed manager revocation, lost responses, self-revocation, and no mutation replay.
- [ ] Verify effective revocation; report ambiguous or unverifiable results as non-success. Metadata discovery must not emit credentials or hashes.
- [ ] Update README/help and architecture mapping; run focused tests, full suite, help under color/no-color, manual mock smoke checks, and build.

## Sources

- [FAB API](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/api_key/api.py)
- [FAB schemas](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/apis/api_key/schema.py)
- [FAB manager](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.2.2/flask_appbuilder/security/sqla/manager.py)

## Decision follow-up

Decision record update required: revise ADR 0023's no-issuance/revocation boundary and record lifecycle/secret-output contracts before implementation.
