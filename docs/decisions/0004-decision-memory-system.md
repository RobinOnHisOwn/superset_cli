# 0004: Decision memory system

- Status: accepted
- Date: 2026-06-05
- Related: `AGENTS.md`, `README.md`, `docs/decisions/README.md`, `docs/plans/README.md`, `docs/plans/2026-06-05-decision-memory-for-agents.md`, `docs/plans/2026-06-05-plan-decision-follow-up-rule.md`, `docs/plans/2026-06-05-document-decision-memory-system.md`

## Context

Future coding agents need durable repository memory for technical reasoning. `README.md` explains what the project does, but not why key choices were made. Plans in `docs/plans/` capture temporary reasoning, but without a durable promotion step, architectural context would remain fragmented across old plans and chat history.

## Decision

Use a layered documentation model:

- `README.md` for project overview and current behavior
- `AGENTS.md` for working rules and mandatory agent workflow
- `docs/index.md` for top-level documentation navigation
- `docs/glossary.md` for repository-specific terminology
- `docs/templates/` for reusable repository-approved documentation templates
- `docs/plans/` for proposed work and temporary implementation reasoning
- `docs/decisions/` for durable ADR-style decision records

Require every non-trivial plan to end with a `Decision follow-up` section that says either:
- `Decision record update required:` with target decision file(s), or
- `No durable decision change.`

Require final task reports to cite the decision record(s) consulted during the work, or explicitly say that no decision record was relevant.

Treat `docs/decisions/` as the canonical long-term memory for why the repository is shaped the way it is.

Update `docs/index.md` in the same workstream whenever a new top-level documentation area is added or an existing documentation layer changes role.

Maintain `docs/glossary.md` when repository-specific terminology changes or important new local terms appear.

Maintain `docs/templates/` as the canonical source for reusable plan, decision-record, and final-report templates.

## Consequences

- Future agents have a predictable place to recover rationale before changing behavior.
- Documentation navigation becomes faster because there is a single entry point to the repository's documentation layers.
- That documentation entry point must be maintained alongside documentation-structure changes.
- A shared glossary reduces ambiguity in local terms used across plans, ADRs, and architecture docs.
- Reusable templates reduce drift in plans, decision records, and final reports.
- Durable reasoning is less likely to be lost in chat transcripts, commit messages, or stale plan files.
- Plans stay useful for execution without becoming the permanent decision log.
- Maintaining this system requires discipline: when durable choices change, the decision log must be updated in the same workstream.
- Final reports become more auditable because future agents and humans can see which decision records informed a change.

## Alternatives considered

### Put all rationale in `README.md`

Rejected because it would mix user-facing overview with detailed historical reasoning and make the main README harder to scan.

### Keep rationale only in plans

Rejected because plans are temporary by nature and are not a reliable long-term retrieval surface for future agents.

### Rely on commit history and code comments

Rejected because important reasoning becomes fragmented, harder to search, and easy for future agents to miss.