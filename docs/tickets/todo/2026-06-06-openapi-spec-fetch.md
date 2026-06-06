# Add OpenAPI spec fetch command

- Status: todo
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset exposes its OpenAPI specification through a dedicated endpoint, but the CLI currently cannot fetch or inspect that schema. For an CLI, access to the live API spec is a useful read-only capability for environment introspection and compatibility checks.

## Definition of done

- [ ] A CLI command fetches the Superset OpenAPI specification for a configured instance.
- [ ] The client wraps the relevant OpenAPI endpoint and returns the raw schema payload safely.
- [ ] Tests cover JSON output, human-readable behavior if any, and standard guard paths.
- [ ] `README.md` and `docs/architecture/README.md` are updated.

## Notes

Prefer preserving the server-provided schema shape instead of reshaping it heavily in the CLI.
