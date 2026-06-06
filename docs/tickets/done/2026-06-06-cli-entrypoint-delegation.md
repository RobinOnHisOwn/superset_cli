# CLI entrypoint delegation

- Status: done
- Priority: medium
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `src/superset_cli/main.py`, `src/superset_cli/cli.py`, `docs/architecture/README.md`

## Context

The package entrypoint is already implemented. `main.py` delegates directly to the Typer app so the installed CLI and module execution path share the same command surface.

## Definition of done

- [x] `main.py` imports the Typer app from `cli.py`.
- [x] The entrypoint `main()` delegates directly to the app.
- [x] Running the module path uses the same CLI registration as the installed command.

## Notes

This is a small but durable runtime wiring behavior.
