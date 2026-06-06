# 0001: Read-only bootstrap scope

- Status: accepted
- Date: 2026-06-05
- Related: `README.md`, `src/superset_cli/cli.py`, `tests/test_cli.py`, `docs/plans/2026-06-05-superset-cli-bootstrap.md`

## Context

This repository started as a bootstrap for an CLI for self-hosted Apache Superset. Early work needed a narrow scope so the project could establish packaging, configuration, CLI patterns, tests, and authentication scaffolding without taking on write-side risk or broad API surface area.

## Decision

Keep the initial product scope read-only.

The CLI may:
- manage local instance configuration
- launch browser-based login and save auth state locally
- validate saved auth state
- read dashboards, charts, datasets, and databases through the Superset REST API

The CLI should not perform write-capable Superset operations unless the scope is explicitly expanded later.

## Consequences

- Command design and tests should preserve a read-only posture by default.
- Future write-capable features require an explicit scope decision instead of incidental expansion.
- Early verification can focus on safe inspection flows and stable JSON output contracts.

## Alternatives considered

### Start with both read and write operations

Rejected for bootstrap because it would increase risk, widen the API surface, and make verification more complex before the core CLI patterns were stable.

### Avoid auth and live API work entirely

Rejected because validating real read access is part of the product value, even in the bootstrap phase.
