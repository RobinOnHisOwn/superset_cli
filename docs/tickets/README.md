# Markdown ticket system

This directory stores lightweight Markdown tickets for repo work.

## Purpose

Use tickets to track actionable work items such as:
- code changes
- docs updates
- plans
- decision-record follow-ups
- cleanup tasks
- research tasks

Tickets are a backlog and workflow tool.
They do not replace:
- `docs/plans/` for non-trivial implementation plans
- `docs/decisions/` for durable technical or process rationale

## Layout

- `todo/` — not started
- `in-progress/` — actively being worked
- `done/` — finished
- `template.md` — canonical ticket template

Folder state is the primary workflow signal.
Each ticket must also include a `Status:` field that matches its folder.

## Lifecycle

1. Create a new ticket in `todo/`.
2. When work starts, move it to `in-progress/` and change `Status:` to `in-progress`.
3. When work is complete, move it to `done/` and change `Status:` to `done`.

## Naming convention

Use sortable filenames:

```text
YYYY-MM-DD-short-topic.md
```

Examples:
- `2026-06-06-add-dataset-pagination-smoke-check.md`
- `2026-06-06-document-auth-storage-state-risk.md`

Keep names short, specific, and readable.

## Duplicate handling

Before creating a new ticket, check `docs/tickets/` for an obvious duplicate.

- If an existing ticket clearly covers the same work, update that ticket instead of creating a new one.
- If overlap is partial or uncertain, create a new ticket and cross-link the related tickets in `Related:`.

## Ticket size

Prefer small, actionable tickets.
If a task is too broad to complete comfortably in one workstream, split it into multiple tickets.

## Choosing the right document

Use a ticket when you need to capture **what should be done**.
Use a plan in `docs/plans/` when you need to capture **how a non-trivial change should be implemented**.
Use a decision record in `docs/decisions/` when you need to preserve **why a durable choice was made**.

## Agent guidance

Agents may create tickets proactively.
They should:
- check for obvious duplicates first
- prefer updating an existing clearly-related ticket
- create a new ticket and cross-link when duplication is uncertain
- keep file location and `Status:` in sync
- keep tickets small and actionable

Agents must still follow the planning and decision-memory rules in `AGENTS.md`.
