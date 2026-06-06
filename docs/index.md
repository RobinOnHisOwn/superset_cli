# Documentation index

This file is the fastest way to find the right repository document.

## Start here

- Project overview and quickstart: [`../README.md`](../README.md)
- Agent workflow and working rules: [`../AGENTS.md`](../AGENTS.md)

## Documentation map

### What the project is

- [`../README.md`](../README.md)
  - purpose
  - quickstart
  - current commands

### How agents must work here

- [`../AGENTS.md`](../AGENTS.md)
  - workflow rules
  - verification expectations
  - TDD and planning requirements
  - documentation maintenance rules

### Why key choices were made

- [`decisions/README.md`](./decisions/README.md)
  - durable technical rationale
  - ADR index
  - decision-record template

### How the code is organized today

- [`architecture/README.md`](./architecture/README.md)
  - module responsibilities
  - command-to-code map
  - test map
  - common edit entry points

### What work is planned or was proposed

- [`plans/README.md`](./plans/README.md)
  - plan format
  - decision follow-up rule
- [`plans/`](./plans/)
  - dated implementation plans and design notes

### How repo work is tracked

- [`tickets/README.md`](./tickets/README.md)
  - Markdown ticket workflow
  - ticket lifecycle
  - duplicate handling
  - ticket template usage

### Reusable documentation templates

- [`templates/README.md`](./templates/README.md)
  - plan template
  - decision-record template
  - final-report template
  - ticket template

### Repository terminology

- [`glossary.md`](./glossary.md)
  - repo-specific terms
  - workflow vocabulary
  - architecture vocabulary

## Which doc should I read?

- Need the quickest project summary? Read `README.md`.
- Need to know how to operate as an agent? Read `AGENTS.md`.
- Need to know why something was done? Read `docs/decisions/`.
- Need to know where to edit? Read `docs/architecture/README.md`.
- Need to understand pending or prior implementation work? Read `docs/plans/`.
- Need to track or review lightweight repo work items? Read `docs/tickets/README.md`.
- Need a starting template for a plan, ADR, final report, or ticket? Read `docs/templates/README.md`.
- Need a definition for repo-specific terms? Read `docs/glossary.md`.

## Maintenance

Update this index in the same workstream when:
- a new top-level documentation area is added
- the role of an existing documentation area changes
- a new canonical entry document replaces an existing one
- a new reusable documentation template area is introduced or reorganized
- glossary terms become outdated because repository terminology changes
