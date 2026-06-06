# 0005: Architecture reference document

- Status: accepted
- Date: 2026-06-05
- Related: `docs/architecture/README.md`, `README.md`, `AGENTS.md`, `docs/decisions/README.md`, `docs/plans/2026-06-05-architecture-overview-doc.md`, `docs/plans/2026-06-05-architecture-reference-adr.md`

## Context

The repository now has durable rationale in `docs/decisions/`, but future agents also need a fast structural map of the current codebase. Rationale answers why choices were made, but it does not replace a concise explanation of module responsibilities, command entry points, and relevant tests. Without a dedicated architecture reference, agents would need to reconstruct structure by repeatedly scanning source files and tests.

## Decision

Maintain `docs/architecture/README.md` as the canonical structural overview for the repository.

This document should provide:
- a concise high-level overview first
- a source tree and module map
- command-to-code mappings for current CLI commands
- a test map
- typical edit entry points for common change types

Use it as a descriptive structural reference, not as the place for durable rationale or workflow rules.

Update it in the same workstream whenever command-to-code mappings, major module responsibilities, or common structural entry points change.

## Consequences

- Future agents can recover code structure faster before editing.
- Structural documentation remains separate from rationale and process documentation.
- `README.md` can stay focused on project overview and quickstart usage.
- The architecture document must be updated when command-to-code mappings, major module responsibilities, or common structural entry points change.

## Alternatives considered

### Keep architecture details only in `README.md`

Rejected because it would overload the main README with implementation detail and make the human-facing overview harder to scan.

### Rely only on source code and tests as the structure map

Rejected because agents can derive structure that way, but the repeated rediscovery cost is high and consistency suffers across sessions.

### Put structural mapping into `AGENTS.md`

Rejected because `AGENTS.md` should focus on workflow rules and operating constraints, not carry a large evolving architecture reference.