# Implement locally actionable API-key lifecycle Todos

**Date:** 2026-10-07

## Goal

Implement current-user API-key metadata discovery and verified revocation without inventing deployment integrations or exposing newly issued credentials.

## Prerequisites and scope

- Verified: pinned FAB 5.2.2 exposes current-user list/get/revoke under `/api/v1/security/api_keys/`, with `can_list`, `can_get`, `can_revoke` on `ApiKey`; list has no pagination. Native revocation ignores the manager's boolean result.
- Verified: existing shared client supplies cookie/JWT/environment-key authentication and CSRF. Existing write opt-in precedes credential access.
- Proposed and selected under autonomous decision authority: `auth api-key list/get/revoke`, with metadata-only `{result: ...}` JSON; revoke succeeds only after matching UUID read-back shows `active=false` and a revocation timestamp. Self-revocation without surviving read access is explicitly unverifiable, not successful.
- Unknown: actual provisioning backend, automation caller, deployment permission registrations, disposable 1Password vault and authorized live acceptance targets. No integration or live mutation is implemented against these unknowns.
- Creation remains unavailable until the secret-safe sink and independently authenticated recovery contract are verified. No cross-user targeting, allowlist CLI default, dependency, package or deployment changes.

## Planned changes

1. Add failing transport-backed CLI tests for metadata filtering, UUID validation before access, opt-in, CSRF, verified/failed/ambiguous revocation, HTTP failures, and forced/no-color help.
2. Add minimal client lifecycle methods and focused callbacks, reusing shared transport; suppress untrusted lifecycle error bodies and filter metadata fields.
3. Update README, architecture, ADR 0023 and lifecycle ticket. Record explicit prerequisites on each remaining ticket without falsely closing any ticket.
4. Run focused tests, full locked suite, CLI smoke checks and build. Leave changes uncommitted in the worktree.

## Verification

All development commands ran from the isolated worktree with `direnv exec "$PWD"`.

- Red: `uv run pytest tests/test_api_key_lifecycle.py -q`: 35 failures because lifecycle commands were absent.
- Focused: `uv run pytest tests/test_api_key_lifecycle.py tests/test_api_key_auth.py tests/test_writes.py tests/test_default_instance.py -q`: 203 passed.
- Locked dependencies: `uv sync --locked --group dev`: succeeded.
- Full: `uv run pytest -v`: 1,032 passed, 13 skipped, Python 3.13.12 on macOS ARM64.
- `uv run superset-cli --help`, `uv run superset-cli auth api-key revoke --help`: succeeded. Tests cover forced-color and no-color help.
- Manual smoke: `uv run superset-cli --config /tmp/key-lifecycle-smoke.yaml auth api-key revoke example 12345678-1234-4234-8234-123456789abc`: exit 1, names missing `--allow-write` and intended revocation; no live request.
- `uv build`: built sdist and wheel. `uv run --isolated --no-project --with dist/*.whl superset-cli auth api-key --help`: succeeded with list/get/revoke in installed wheel.
- `git diff --check`: passed. Full suite includes documentation link checks after lifecycle ticket relocation.
- Python 3.12 matrix attempt: `UV_PROJECT_ENVIRONMENT=/tmp/superset-key-lifecycle-py312 uv run --python 3.12 --locked pytest -v` blocked because no 3.12 interpreter is available and environment disables downloads. Linux CI and live deployments remain untested.
- `specdocs_validate`: reports an existing `docs/architecture/README.md` filename-pattern error in the tool's original workspace. Worktree docs use repository templates; link checks pass.
- Consulted ADRs 0023 and 0024, and the write-guard contract recorded in repository instructions/ADR 0009. No live Superset calls, role writes, key issuance or vault writes performed.

The local main checkout was one ticket-research commit ahead of fetched `origin/main`. Its five tickets and research plan were initially copied into the fresh worktree before updating status/links. During requested pre-commit review, the original ticket-research commit was cherry-picked as a separate prerequisite so the implementation commit preserves a real ticket relocation rather than duplicating research. No merge or modification of the human checkout was performed. Four tickets remain todo, lifecycle remains in-progress pending safe create, and existing cache live acceptance remains blocked. The initial implementation was left uncommitted. Follow-up user authorization permits staging and committing the reviewed work; repository instructions prohibit pushing. No push or PR created.

Workflow note: `direnv exec PATH` loads the environment but does not change process cwd. Always `cd` to the verified worktree first; otherwise tests/build can silently target the human checkout.

## Decision follow-up

Decision record update required: `docs/decisions/0023-environment-bound-api-keys.md` for the current-user metadata/revocation exception, output contract and verification boundary.
