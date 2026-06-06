# Decision log

This directory is the durable technical memory for this repository.

## Purpose

Use these files to answer:
- why was this done?
- what alternatives were considered?
- what trade-offs were accepted?
- what assumptions should future changes preserve or revisit?

`README.md` explains what the project does.
`AGENTS.md` explains how agents must work here.
`docs/decisions/` explains why key technical choices were made.

## How to use this directory

- Read the relevant decision records before planning or changing behavior.
- Add a new record when a change introduces or reverses a durable technical decision.
- Update an existing record when the same decision evolves.
- Link decisions to relevant plans in `docs/plans/`, code paths, and tests when possible.
- Final task reports should cite the decision record(s) consulted, or explicitly say that no decision record was relevant.
- Every non-trivial plan in `docs/plans/` must end with a `Decision follow-up` section that says either:
  - `Decision record update required:` followed by target decision file(s), or
  - `No durable decision change.`

## File naming

Use numbered, stable filenames:
- `0001-short-decision-name.md`
- `0002-another-decision.md`

Keep one durable decision per file.

## Reusable template

For a copyable starting point, use `../templates/decision-record-template.md`.

## Suggested template

```md
# 000X: Title

- Status: accepted | proposed | superseded
- Date: YYYY-MM-DD
- Related: docs/plans/..., src/..., tests/...

## Context

## Decision

## Consequences

## Alternatives considered
```

## Current decision records

- [0001: Read-only bootstrap scope](./0001-read-only-bootstrap-scope.md)
- [0002: Local config and auth state storage](./0002-local-config-and-auth-state-storage.md)
- [0003: Browser login with Playwright and saved storage state](./0003-browser-login-with-playwright-and-saved-storage-state.md)
- [0004: Decision memory system](./0004-decision-memory-system.md)
- [0005: Architecture reference document](./0005-architecture-reference-document.md)
- [0006: Markdown ticket system](./0006-markdown-ticket-system.md)
- [0007: Superset CLI product and package name](./0007-superset-cli-product-and-package-name.md)
