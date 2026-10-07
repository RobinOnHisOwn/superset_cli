# Refresh companion-skill preflight and command recipes

- Status: done
- Priority: high
- Type: docs
- Created by: agent
- Created at: 2026-10-06
- Related: [plan](../../plans/2026-10-06-remaining-open-todos.md), `tests/test_skill_recipes.py`, `README.md`

## Context

Old recipes omitted instance arguments and recommended obsolete unconditional CSRF/Zen/cookie workarounds. Runtime skill files must not be patched as substitutes for managed sources.

## Definition of done

- [x] Refresh authoritative shared companion skill source in an isolated source worktree, leaving deployed copies untouched.
- [x] Correct `charts update INSTANCE CHART_ID` and `dashboards diff INSTANCE A B`; verify actual CLI parsing with mocked requests.
- [x] Add executable/provenance/capability preflight, JSON-first discovery, precise command ordering, and bounded auth recovery.
- [x] Route custom API calls and optional browser verification through existing authenticated recipes.
- [x] Replace universal CSRF/Zen claims with verified selected-build diagnostics; prohibit replacement transports and credential extraction.
- [x] Explain stale query context, explicit write guards, and separate persistence/query/render verification.
- [x] Execute a representative discovery/validate/update/get/data/diff/API workflow with mocked HTTP and no cookie extraction; verify missing write opt-in makes no request.

## Source ownership and handoff

Source branch: `docs/superset-open-todos` in the shared skills repository.

- `skills/datateam/superset-cli/SKILL.md`
- `skills/datateam/superset-api-troubleshooting/SKILL.md`
- Shared README catalog updated.

The unmanaged legacy `superset-api-write-workarounds` had no source registration. Its corrected replacement is now authoritative in the shared source repository and uses a distinct name to avoid a runtime-copy name collision. No deployed files, installation, activation, or other agent's existing source branch were modified.

Frontmatter, requirements, safe examples, and shared README links were checked. Runnable mocked workflow evidence lives in `tests/test_skill_recipes.py`. Independent-agent/live-browser evaluations were not performed; this is source and command verification, not a claim of deployed skill behavior.

## Rollout remaining for the operator

Integrate the shared source, retire the unmanaged legacy skill through authorized setup, reload, and verify discovery. Configuration activation/publication was not authorized. This deployment handoff is distinct from the completed source-refresh implementation.
