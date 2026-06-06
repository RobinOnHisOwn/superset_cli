# 0006: Markdown ticket system

- Status: accepted
- Date: 2026-06-06
- Related: `AGENTS.md`, `docs/index.md`, `docs/glossary.md`, `docs/tickets/README.md`, `docs/tickets/template.md`, `docs/plans/2026-06-06-markdown-ticket-system.md`

## Context

The repository already has durable rationale in `docs/decisions/`, temporary implementation planning in `docs/plans/`, and workflow rules in `AGENTS.md`. It did not yet have a lightweight in-repo backlog system for tracking actionable repo work across sessions. Relying only on chat history or ad hoc notes would make small follow-ups easy to lose, while using decision records or implementation plans for simple task tracking would overload those documentation layers.

## Decision

Add a dedicated Markdown ticket system in `docs/tickets/`.

The system uses three status folders:
- `docs/tickets/todo/`
- `docs/tickets/in-progress/`
- `docs/tickets/done/`

Folder location is the primary workflow state. Each ticket must also include a `Status:` field that matches its folder.

Tickets may track any repo work, including code changes, documentation work, planning follow-ups, decision-record follow-ups, cleanup, and research.

Agents may create tickets proactively, but they must first check for obvious duplicates and prefer updating an existing clearly-related ticket. If overlap is uncertain, they should create a new ticket and cross-link related work.

Tickets capture what should be done. They do not replace:
- `docs/plans/` for non-trivial implementation planning
- `docs/decisions/` for durable rationale

## Consequences

- The repository gets a lightweight, agent-friendly backlog that persists in versioned Markdown.
- Humans and agents can both see workflow state directly from the directory structure.
- Metadata drift risk is reduced by requiring both folder state and an in-file `Status:` field.
- Agents can record follow-up work without waiting for a separate external ticketing system.
- The repository gains another top-level documentation area that must be maintained in `docs/index.md` and `docs/glossary.md`.
- Duplicate tickets remain possible, so the workflow relies on an obvious-duplicate check and cross-linking rather than perfect deduplication.

## Alternatives considered

### Use `docs/plans/` as the task backlog

Rejected because plans are for non-trivial implementation reasoning and should not become the general queue for small actionable work items.

### Keep all tickets in one folder with only a `Status:` field

Rejected because folder-based workflow is easier to scan quickly, especially for agents working from the file tree.

### Require humans to create all tickets

Rejected because this repository explicitly wants agents to be able to create follow-up work proactively.
