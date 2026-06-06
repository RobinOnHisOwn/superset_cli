# 0007: Superset CLI product and package name

- Status: accepted
- Date: 2026-06-06
- Related: `docs/plans/2026-06-06-superset-cli-rename.md`, `pyproject.toml`, `src/superset_cli/`, `README.md`, `AGENTS.md`, `.github/workflows/ci.yml`, `tests/test_cli.py`, `tests/test_repo_files.py`

## Context

The initial bootstrap named the product `superset-agent-cli` and exposed the console command as `superset-agent`. That name overfit one usage style. The product should remain useful for agents, but it should also be positioned as a general-purpose CLI for self-hosted Apache Superset, including human and other automation contexts.

## Decision

Rename the product, package, and command surfaces to `superset-cli`.

This includes:
- Python distribution name: `superset-cli`
- console command: `superset-cli`
- Python package path: `superset_cli`
- current repository docs and CI smoke checks updated to the new name

The rename is intentionally broad and replaces the old product identity rather than keeping parallel public names.

## Consequences

- The CLI is positioned as a broader automation tool instead of an agent-specific product.
- Current code paths, imports, and documentation are simpler because they align around one name.
- Existing users of the old `superset-agent` command must switch to `superset-cli`.
- Any downstream automation that imported `superset_agent_cli` must switch to `superset_cli`.

## Alternatives considered

### Keep `superset-agent-cli` as the primary product name

Rejected because it narrows the perceived scope of the product too early and makes non-agent automation use cases feel secondary.

### Keep the old internal package name but rename only the command

Rejected because it would leave long-term drift between the user-facing product name and the implementation surface.

### Support both old and new public names indefinitely

Rejected because it increases maintenance burden and prolongs ambiguity around the product identity.
