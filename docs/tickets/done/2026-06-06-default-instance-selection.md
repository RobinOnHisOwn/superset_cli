# Design default instance selection

- Status: done
- Priority: medium
- Type: research
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/config.py`, `src/superset_cli/models.py`, `README.md`, `docs/decisions/0001-read-only-bootstrap-scope.md`

## Context

Every command currently requires an explicit instance name. A default-instance mechanism would improve day-to-day ergonomics, but it would also change CLI behavior and may affect config shape or command precedence. The repository rules require asking before changing CLI defaults, so the contract should be designed before implementation.

## Definition of done

- [x] Candidate approaches are compared, such as config-backed default instance, environment variable override, or explicit global flag.
- [x] Precedence, backward compatibility, and failure behavior are documented.
- [x] A recommended contract is captured in a short plan or decision follow-up if needed.
- [x] If implementation is approved later, a follow-up code ticket is created or linked.

## Notes

Ask-first boundary applies here because this work may change CLI defaults.
