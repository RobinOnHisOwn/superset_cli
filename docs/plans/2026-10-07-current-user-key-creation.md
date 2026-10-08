# Implement current-user API-key creation

**Date:** 2026-10-07

## Goal

Implement the focused [creation ticket](../tickets/in-progress/2026-10-07-current-user-api-key-creation.md) without weakening secret-output or mutation guards.

## Verified contracts and selected design

- FAB 5.2.2 native POST accepts name, optional scopes and ISO expires_on, returns a one-time key plus UUID, and targets only the authenticated user. Existing list/get/revoke supply owner-scoped discovery and verified stored revocation.
- Superset 6.1.0 `/me/roles/` returns effective role-to-permission pairs via `bootstrap_user_data`; require all four ApiKey grants and CSRF read access, plus an active identified user. Native list verifies registration/storage and supplies a before-image.
- Installed `op` 2.33.1 help and API Credential template verify JSON stdin create, piped JSON edit, immutable IDs, explicit account/vault selection and captured `get --reveal --format json --cache=false`. No authenticated vault operations have been run.
- Choose required operation UUID, explicit account/vault, and mandatory timezone-aware expiry no more than 90 days ahead. FAB's model uses naive DateTime and local `datetime.now()` comparisons: require an explicitly verified server IANA clock timezone, convert input to naive wall time, verify stored expiry and reject ambiguous DST folds. Name gets a unique operation marker; preflight refuses an existing operation. No scopes option because native stored scopes are not enforced authorization.
- Create and read/edit a dedicated non-secret placeholder item before issuance; then use the same immutable item/vault IDs for delivery and compare secret/UUID metadata in memory. No overwrite of existing items.
- On failure after sending POST, identify the newly created key from owner-scoped metadata and its operation marker, revoke using the original caller, and read back stored state. If reconciliation or cleanup is ambiguous, return non-success with only recovery IDs. No automatic POST or item-create replay. Native names are not idempotency or uniqueness constraints: never share an operation UUID across concurrent invocations; a timed-out create can still complete after reconciliation.
- Unknown: live 1Password account/vault and authorized Superset test target. Runtime preflight must fail closed; disposable end-to-end release acceptance remains blocked without supplied targets. No cross-user/service provisioning is implemented.

## Planned changes

1. Add a focused ticket, move it to in-progress, and link the split from the existing lifecycle/service tickets.
2. Write failing CLI tests using fake HTTP and subprocess adapters, including all failure paths and distinctive secret leak checks.
3. Add a small issuance module using stdlib subprocess and existing client/auth/CSRF transport, plus a guarded create callback. Keep issued values out of exceptions, argv, environment and files.
4. Update ADR 0023 and add ADR 0025, README and architecture. Run focused tests, full suites for both supported Python versions, help and built-package smoke checks.
5. Leave changes uncommitted unless explicitly requested; do not push or mutate live instances/vaults.

## Verification

Research sources: pinned FAB API/schema, pinned Superset users API and `views/utils.py`, official 1Password item documentation and local unauthenticated help/template reads. Consulted ADRs 0009, 0010, 0023 and 0024 and existing lifecycle tests; recorded the creation decision in ADR 0025.

- Initial failing creation tests preceded implementation. Review also reproduced redirect replay in shared cookie-auth mutations and credential leakage through allowed `OP_SESSION_*` aliases. Regression tests failed before fixing shared transport and excluding caller bearer/cookie values from the subprocess environment.
- Focused verification: `uv run pytest tests/test_api_key_creation.py tests/test_client.py -q` — 91 passed.
- Full locked suites using CI's pinned uv 0.12.23: Python 3.13.12 and 3.12.15 — 1,085 passed, 13 skipped on each. Help tests cover forced-color and no-color environments.
- `uv sync --locked --group dev`, top-level/create help, `uv build`, and isolated wheel/sdist create-help smoke checks passed. Manual create invocation without `--allow-write` exited 1 before accessing a nonexistent explicit config; it named the missing flag and intended mutation.
- Local unauthenticated `op item template get 'API Credential' --format json --cache=false` accepted the inspected flags. No live vault or Superset writes were performed.
- Documentation-link tests and `git diff --check` passed. Workspace `specdocs_validate` still reports the existing architecture README filename/pattern error.
- Ubuntu/GitHub Actions and disposable-target delivery, expiration and rejection acceptance remain unverified. The ticket stays in-progress; local tests are not release acceptance.

## Decision follow-up

Decision record update required: `docs/decisions/0010-write-scope-expansion.md`, `docs/decisions/0023-environment-bound-api-keys.md` and `docs/decisions/0025-current-user-api-key-creation.md` (updated in this workstream).
