# Research guest-token auth support

- Status: done
- Priority: low
- Type: research
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/decisions/0001-read-only-bootstrap-scope.md`, `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `README.md`, `docs/architecture/README.md`

## Context

Superset supports guest tokens for embedded dashboard use cases, but guest tokens are not a drop-in replacement for normal CLI API auth. If embedded workflows matter to this repository later, the project should first decide whether guest-token support belongs in this CLI and how separate it should remain from normal auth flows.

## Definition of done

- [x] The valid guest-token use cases for this repository are documented.
- [x] The distinction between general API auth and embed-specific guest-token flows is documented.
- [x] Any prerequisite permissions, CSRF needs, and embedding constraints are documented.
- [x] A recommendation is made to defer, reject, or pursue follow-up implementation work.

## Notes

Keep this work separate from the main auth roadmap unless a real embedding use case appears.
