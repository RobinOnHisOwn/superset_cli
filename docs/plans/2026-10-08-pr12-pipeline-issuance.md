# Align PR 12 with caller-owned secret handling

**Date:** 2026-10-08

## Goal

Replace the obsolete mandatory 1Password implementation with guarded current-user pipeline output on current `origin/main`, without changing the newer service-account tickets.

## Verified facts and design

- PR 11 replaced built-in 1Password handling with separate explicit secret-output opt-in. PR 12 is one commit ahead and five behind main; its issuance-ticket conflict reflects that deliberate requirements change.
- Pinned FAB 5.2.2 POST creates only for the authenticated user. Its GET rejects keys owned by another user. Native response schemas do not expose owner IDs; verify owner-scoped GET and unchanged active caller identity before emitting.
- Existing list/get/revoke, CSRF, transport and environment syntax validation are reusable. Require lifecycle grants, a unique operation UUID, future timezone-aware expiry within 90 days and an operator-verified IANA server timezone. No scopes authorization or cross-user endpoint is invented.
- Require both `--allow-write` and `--secret-output` before credentials/network. Without the latter, refuse issuance rather than silently discard a one-time key. Reject `--json` with secret mode. Explicit success writes only the key plus newline to stdout; secret-free recovery metadata goes to stderr. A flush is not downstream storage proof.
- Preserve original-caller reconciliation/verified revocation on failure, including partial output, broken pipes and interruptions. Never replay a sent mutation. Runtime callers receive no lifecycle grants. No 1Password processes, vaults, environment export, files or downstream verification.
- Python ignores SIGPIPE and raises BrokenPipeError; flush inside the guarded operation and suppress repeated exit flush against a broken real stdout descriptor. Never restore SIGPIPE's default handler.
- Unknown: authorized isolated Superset target, actual server timezone and independent operator recovery. Live acceptance remains blocked; local mocks are not delivery/expiry/rejection evidence.

## Planned changes

1. Use an isolated worktree with the published PR head as its ancestor, then restore the freshly fetched main working-tree snapshot before rebuilding the feature. This permits a future normal fast-forward PR update without merging or rewriting history. Leave main and the original published branch untouched; do not publish.
2. Write failing pipeline/guard/ownership/recovery/help and shared mutation redirect tests first.
3. Implement the minimum native current-user emitter using existing client/auth helpers; remove all mandatory vendor-sink assumptions from the replacement change.
4. Update README, architecture, glossary, current-user ticket and decisions; keep PR 11's service-user research/output/acceptance tickets unchanged.
5. Verify targeted tests, both supported Python versions with locked CI uv, CLI help/guard and isolated built packages. Report remote-update limitations explicitly.

## Verification

Consulted ADRs 0009, 0010, 0023 and 0024, PR 11's service-user tickets, pinned FAB API/schema and Python SIGPIPE documentation. Replaced ADR 0025 with the approved caller-owned pipeline contract.

- New creation tests failed first: 32 failures because main has no create callback. Broken-pipe regression reproduced 21 DELETE sends before shared transport correction. Four guard tests failed before routing callback guard diagnostics to stderr; the missing-state test failed before redirecting its preflight diagnostic. All are now passing.
- Focused command: `uv run pytest tests/test_api_key_creation.py tests/test_client.py tests/test_api_key_auth.py tests/test_api_key_lifecycle.py -q` — 128 passed, including forced-color/no-color help.
- Full locked suites with CI uv 0.12.23: Python 3.13.12 and 3.12.15 on Darwin — 1,072 passed, 13 skipped each. `uv sync --locked --group dev`, top-level/create help, `uv build`, isolated wheel create-help and isolated sdist module import passed. Distributions remain version 0.3.1.
- Manual installed-executable invocation with only --allow-write and a nonexistent explicit config exited 1, left stdout empty and named --secret-output on stderr. No live issuance, external sink or vault access occurred.
- Constructed an unreferenced working-tree snapshot using Git blob/tree objects (no index, branch, commit or checkout updates). Read-only three-way preview against current main reported no conflict markers. Service-account Todo files and release/version files compare byte-for-byte with main. The published PR head remains an ancestor of the local fix branch for a later normal fast-forward update.
- `git diff --check` and documentation-link tests passed. Workspace specdocs validation still reports the existing architecture README filename/pattern mismatch.
- GitHub CI on the corrected change, Ubuntu behavior and authorized isolated ownership/expiry/rejection acceptance remain unverified. The remote PR is unchanged until published; no push, merge or history rewrite was performed.

## Decision follow-up

Decision record update required: `docs/decisions/0010-write-scope-expansion.md`, `docs/decisions/0023-environment-bound-api-keys.md` and replacement `docs/decisions/0025-current-user-api-key-creation.md`.
