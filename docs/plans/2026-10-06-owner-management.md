# Guarded chart and dashboard ownership

**Date:** 2026-10-06

## Goal

Implement six owner discovery/replacement/membership tickets without changing existing get/update JSON or permitting implicit writes.

## Prerequisites and research

- **Verified:** isolated `fix/autonomous-todos` worktree, existing chart/dashboard getters and CSRF-protected update methods, shared literal `--allow-write` helper, ADRs 0009 and 0010.
- **Verified:** pinned Superset 6.0 sources: chart/dashboard schemas accept integer owner arrays; details return owner objects; `views/base_api.py` related query accepts `filter` (string), `page`, and `page_size`; related responses preserve `count` and `result` (`value`, `text`, optional `extra`). `commands/utils.py` retains non-admin callers and treats omission differently from empty replacement.
- **Unknown:** live deployment version, permissions, and concurrency/precondition support. No live access needed for implementation. Each write checks the target OpenAPI PUT owner-array contract and actual owner details before PUT. Candidate discovery checks its documented query schema. No editor/viewer or subject-ID conversion.
- **Selected contract:** flat `owners`, `owner-candidates`, `owners-set`, `owners-add`, `owners-remove` under charts/dashboards. Repeated positive `--owner-id`; replacement emptiness requires `--clear`, removal of the last owner requires `--clear`. User requested implementation with the ownership safety guardrail; existing JSON contracts remain unchanged.

## Planned changes

1. Copy the six untracked tickets into this worktree's in-progress folder without altering their source worktree.
2. Write failing transport-backed tests for both resources: owners/empty/missing/malformed fields, candidates/filter/pagination, ID/slug/UUID resolution, explicit opt-in including no-ops, integer validation, owner-only bodies, non-admin retention, unsupported schemas, API failures, and failed read-back.
3. Extend existing client/CLI patterns, sharing only the matching chart/dashboard owner flow. No new dependency or generic resource framework.
4. JSON inspections return `resource`, numeric `id`, and owner objects; candidates preserve the server envelope. Mutations additionally report operation, requested IDs, write_performed, verified, matches_requested, and warning. Read-back failures or mismatches emit that evidence and exit 1; no mutation retries.
5. Document non-admin retention, independent ownership, explicit clear, and non-atomic read-modify-write. Record the durable compatibility/read-back contract in ADR 0020 and update architecture/README/tickets.

## Verification

- First run new tests red for missing commands/methods, then focused green.
- Full `uv run pytest -v`, optional browser suite when available, CLI help/manual mocked transport smoke checks, `uv build`, documentation links and `git diff --check`.
- No real browser profiles, interactive login, live writes, commit, push, merge, or publication.

## Completion evidence

All six tickets are complete in this worktree's `docs/tickets/done/`; their original untracked source-worktree files were left unchanged.

Files: `src/superset_cli/client.py`, `src/superset_cli/cli.py`, `tests/test_owners.py`, README, architecture overview, ADR 0020/decision index, this plan, and six done tickets. No dependency/config/default/get/update JSON change. Reusable ownership safety recipes were saved in the external authoritative companion `skills/datateam/superset-cli/SKILL.md` worktree; `skill_manage` cannot locate that source under deployed `~/.pi`, so no deployed copy was created or edited.

- Initial owner tests failed for missing commands; additional red/green checks caught wrong-resource IDs (including encoded numeric IDs), malformed/conflicting capabilities, boolean IDs before deduplication, URL-route-changing identifiers, and false no-op claims after network timeout.
- `direnv exec "$PWD" uv run pytest tests/test_owners.py tests/test_writes.py tests/test_default_instance.py -q`: focused regression run passed.
- Final `direnv exec "$PWD" uv run --with playwright pytest -v`: **843 passed**, no skips or failures; includes **187 owner cases**, including nested type/items schema conflicts and route confinement.
- Final core `direnv exec "$PWD" uv run pytest -v`: **830 passed, 13 optional-browser skips**.
- Final `uv run pytest tests/test_owners.py tests/test_docs_links.py -q`: **189 passed** after moving/completing tickets and editing documentation.
- `uv build`: final unpublished 0.2.0 wheel and sdist built successfully. The final rebuilt wheel was installed in an isolated `/tmp` environment; wheel import and owner-command help passed with source import excluded. No user-tool install/upgrade was performed.
- `uv run superset-cli --help`, `charts owners-set --help`, and `dashboards owner-candidates --help`: passed. Manual `uv run superset-cli charts owners-add prod 7 --owner-id 3` exits **1** naming missing `--allow-write`, without creating a client or requiring credentials.
- `git diff --check`: clean in both worktrees. Six done-ticket statuses/checkboxes and README owner examples' Bash syntax/120-character line ceiling verified. Human checkout remains clean. Specdocs still reports the existing architecture-README plan-filename classification error, not clean validation.

Consulted ADRs 0009/0010 and pinned Superset 6.0 API/schema/query/filter/owner-computation sources. Target version/permissions remain unverified by live acceptance; runtime capability checks fail closed. Read-modify-write remains non-atomic. Acknowledged write/read-back failure, requested/effective mismatch, and uncertain network outcome are distinct; no automatic mutation retries. No live mutation, user browser inspection, commits, pushes, merges, or publication.

## Decision follow-up

Decision record update required: completed in `docs/decisions/0020-guarded-resource-owners.md` and linked from the decision index. ADRs 0009 and 0010 were reused without expanding their write scope.
