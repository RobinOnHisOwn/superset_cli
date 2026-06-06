# Repository glossary

This glossary defines repository-specific terms used across the documentation set.

## Architecture reference document

`docs/architecture/README.md`, the canonical structural map of modules, commands, tests, and common edit entry points.

## Command-to-code map

A mapping from a CLI command to the main implementation files and tests that define or verify it.

## Common structural entry points

The primary files an agent should read first when making a certain class of change, such as output formatting, config storage, or auth-state handling.

## Decision follow-up

The required final section in every non-trivial plan. It must say either:
- `Decision record update required:` with target decision file(s), or
- `No durable decision change.`

## Decision record

A durable Markdown record in `docs/decisions/` that captures context, the chosen decision, consequences, and alternatives considered.

## Decision log

The collection of all decision records in `docs/decisions/`.

## Documentation index

`docs/index.md`, the top-level map that routes readers to the right documentation layer.

## Durable decision

A technical or process choice whose reasoning should persist across sessions because future work is likely to depend on it.

## Final report

The completion summary for a task. In this repository it should include files changed, commands run, verification results, consulted decision records, and remaining risks or unverified areas.

## Markdown ticket system

The lightweight in-repo backlog in `docs/tickets/` used to track actionable repo work in Markdown files.

## Read-only posture

The current product-scope constraint that the CLI should not perform write-capable Superset operations unless that scope is explicitly expanded.

## Repository-approved templates

The canonical templates in `docs/templates/` for plans, decision records, and final reports.

## Storage state

The Playwright browser session data saved to `storage-state.json`, primarily used here to persist cookies for later API access.

## Ticket lifecycle

The required movement of a ticket through `docs/tickets/todo/`, `docs/tickets/in-progress/`, and `docs/tickets/done/`, with the ticket's `Status:` field kept in sync with its folder.

## Top-level documentation area

A major documentation layer with a distinct purpose in the repository, such as `README.md`, `AGENTS.md`, `docs/decisions/`, `docs/architecture/`, `docs/plans/`, `docs/tickets/`, or `docs/templates/`.
