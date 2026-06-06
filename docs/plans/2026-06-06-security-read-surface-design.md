# Design: security and admin read surface

## Status

Research only. No code changes.

## Scope check

Superset exposes a wide read surface under FAB security and Superset-specific resources, including:

- `/api/v1/security/role/`, `/api/v1/security/role/{pk}`
- `/api/v1/security/user/`, `/api/v1/security/user/{pk}` (where exposed by the FAB version)
- `/api/v1/security/permissions/`
- `/api/v1/security/permissions-resources/`
- `/api/v1/security/guest_token/` (out of scope — covered in the guest-token research ticket)
- `/api/v1/rowlevelsecurity/`, `/api/v1/rowlevelsecurity/{pk}`

This is a broad and sensitive surface. The goal of this design is to **narrow** before adding commands.

## Recommended initial subset

Add only these read commands in the first implementation:

1. `security roles list <instance> [--search ...]`
2. `security roles get <instance> <pk>`
3. `security users list <instance> [--search ...]`
4. `security users get <instance> <pk>`
5. `security rls list <instance>`
6. `security rls get <instance> <pk>`

Defer for a separate later ticket:

- `security permissions list/get`
- `security permissions-resources list/get`

These two enumerate every action × resource pair, which is large, noisy, and not commonly useful as the first thing an agent needs.

## Risks

- Sensitive output: role and user payloads may include email addresses and last-login timestamps. The CLI must not log secrets, but it should expose only fields that are already visible in the Superset UI for the authenticated user. Human output should be summary-style; the raw payload is only available via `--json`.
- Permissions: a non-admin user may not be authorized to call these endpoints. The existing `_api_errors()` handler now returns a clean HTTP-error message; this is sufficient. No additional permission-checking logic is required.
- Discoverability: an agent could enumerate users to map an organization. This is a documented risk of any Superset admin token; the CLI just exposes endpoints that are already accessible via the API. No new exposure is introduced.
- Naming: `users` and `roles` already exist in many CLIs. Prefixing them under `security` (as Superset itself does) avoids collisions with hypothetical future top-level command groups.

## Output shape

- Reuse the existing list/get pattern (paged, JSON or summary human output, shared `_api_errors()`).
- Human-output line formats:
  - Roles: `{id}: {name}`
  - Users: `{id}: {username} ({email})`
  - RLS: `{id}: {name} (filter_type={filter_type})`

## Recommendation

Create three follow-up implementation tickets, one per resource (roles, users, RLS), all explicitly read-only. Do **not** implement permissions or permissions-resources in the same workstream.

Follow-up tickets:

- `2026-06-06-security-roles-read-commands.md`
- `2026-06-06-security-users-read-commands.md`
- `2026-06-06-security-rls-read-commands.md`

## Decision follow-up

No durable decision change yet. A decision record should be added when the subset is implemented, capturing why permissions/permissions-resources stay out of scope unless explicitly requested.
