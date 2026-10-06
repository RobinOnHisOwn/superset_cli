# 0013: Narrow security read surface

- Status: accepted
- Date: 2026-10-06
- Related: `docs/plans/2026-10-06-autonomous-todos.md`, `docs/plans/2026-06-06-security-read-surface-design.md`, `tests/test_security_explore_reads.py`

## Context

The security API includes large permissions catalogs and sensitive user metadata. The initial read commands need only roles, users, and row-level-security rules.

## Decision

Expose list/get commands under `security roles`, `security users`, and `security rls`. Use plural FAB paths `/api/v1/security/roles/` and `/api/v1/security/users/`, matching published Superset documentation and existing write methods; the older design's singular paths are obsolete. The user API may require server-side `FAB_ADD_SECURITY_API` and appropriate permissions. Fail normally when the server does not expose or authorize it.

Human output includes only ID and name/username. Explicit `--json` returns the server's resource payload. Do not add permissions or permissions-resources catalog commands in this workstream. Existing write commands and their opt-in guard remain unchanged.

## Consequences

Operators can inspect the approved subset without enumerating every action/resource permission pair. User JSON may contain personal metadata and must be handled accordingly. No live security enumeration is needed for tests.

## Alternatives considered

### Add the entire security catalog

Rejected: it is large, noisy, and unnecessary for the requested role/user/RLS reads.
