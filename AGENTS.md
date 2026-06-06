# AGENTS.md

## Mission

This repository builds `superset-cli`, a CLI for self-hosted Apache Superset.

Current product scope is **read-only**:
- local instance config management
- Playwright-based browser login scaffold
- saved auth-state inspection and validation
- read-only Superset REST access for dashboards, charts, datasets, and databases

Do not expand the product beyond read-only behavior unless the user explicitly asks for it.

## Instruction priority

Follow instructions in this order:
1. explicit user request
2. this file
3. README and nearby docs
4. existing code patterns

If instructions conflict or the safest path is unclear, stop and ask.

## Project map

- `src/superset_cli/` — application code
- `tests/` — pytest suite; treat tests as executable spec
- `docs/index.md` — top-level map of repository documentation
- `docs/glossary.md` — repository-specific terminology used in docs, plans, and architecture notes
- `docs/templates/` — reusable templates for plans, decision records, and final reports
- `docs/plans/` — written plans and design notes
- `docs/tickets/` — lightweight Markdown ticket system for repo work tracking
- `docs/decisions/` — durable decision log; this is the primary "why" memory for future agents
- `docs/architecture/` — structural map of the codebase; use this for module responsibilities and command-to-code entry points
- `README.md` — human-oriented project overview and commands
- `pyproject.toml` — dependencies, packaging, Python version
- `devenv.nix` / `devenv.yaml` — local development environment

## Environment and working commands

Prefer these commands:

```bash
devenv shell
uv sync --group dev
uv run pytest -v
uv run pytest tests/test_cli.py -v
uv run superset-cli --help
uv build
uv run playwright install chromium
```

Use `uv` to run Python commands. Prefer `devenv shell` before development work.

## Golden workflow (mandatory)

For any task beyond a tiny docs edit:

1. **Research first.** Check relevant docs, APIs, libraries, and existing repo patterns before changing code.
2. **Read first.** Read all relevant files immediately before referencing or editing them. Read nearby tests before implementation. Read relevant files in `docs/decisions/` before planning or changing behavior. Read `docs/index.md` when you need the top-level documentation map. Read `docs/glossary.md` when repository-specific terminology is unclear. Read `docs/templates/README.md` when you need repository-approved doc templates. Read `docs/architecture/README.md` when you need the current structural map of modules, commands, and tests.
3. **Plan first.** Write a short plan to `docs/plans/YYYY-MM-DD-<topic>.md` before any non-trivial change. Every plan must end with a `Decision follow-up` section that says either `Decision record update required:` with the target file(s), or `No durable decision change.`
4. **TDD always.** Write or update a failing test first.
5. **Implement minimally.** Make the smallest change that satisfies the test and the request.
6. **Verify incrementally.** Run focused tests first, then broader verification.
7. **Capture durable reasoning.** If you made or changed a lasting technical decision, add or update a record in `docs/decisions/` and link it from the plan.
8. **Report evidence only.** Never claim success without command output or other concrete evidence.

## TDD rules

TDD is required for all code changes.

- Start by adding or updating tests in `tests/`.
- Confirm the new or changed test fails for the expected reason.
- Implement the minimum code needed to make it pass.
- Re-run the targeted test, then the broader suite.
- Never remove, weaken, or bypass a test just to get green results.

For CLI changes:
- test both human-readable output and `--json` output when applicable
- preserve existing JSON output shape unless the contract is intentionally changed
- when changing the contract, update tests and docs in the same task

## Decision memory rules

- Treat `docs/decisions/` as the canonical long-term memory for why this repository works the way it does.
- Before planning or implementation, read the most relevant decision record(s) for the area you are changing.
- Use `docs/plans/` for proposed work and temporary reasoning.
- Every non-trivial plan must include a final `Decision follow-up` section with one of two outcomes: `Decision record update required:` or `No durable decision change.`
- Promote any durable outcome from a plan into `docs/decisions/`.
- Keep one decision per file with stable headings such as `Status`, `Context`, `Decision`, `Consequences`, and `Alternatives considered`.
- Cross-link decision records to relevant plans, code paths, and tests when possible.
- Do not bury important rationale only in chat, commit messages, or code comments.

## Markdown ticket system

- Use `docs/tickets/` for lightweight repo work tracking.
- Ticket folders are the primary workflow state:
  - `docs/tickets/todo/`
  - `docs/tickets/in-progress/`
  - `docs/tickets/done/`
- Every ticket must also include a `Status:` field that matches its folder.
- Agents may create tickets proactively for code, docs, plans, decisions, cleanup, research, and follow-up work.
- Before creating a ticket, check `docs/tickets/` for an obvious duplicate.
- If an existing ticket clearly covers the same work, update that ticket instead of creating a new one.
- If overlap is uncertain, create a new ticket and cross-link related tickets.
- Keep tickets small and actionable; split broad work into multiple tickets.
- Starting work on a ticket should move it to `in-progress/`.
- Finishing work on a ticket should move it to `done/`.
- Tickets capture what should be done. They do not replace `docs/plans/` for non-trivial implementation planning or `docs/decisions/` for durable rationale.

## Coding rules

- Prefer extending existing patterns in `cli.py`, `client.py`, `config.py`, `auth.py`, and `models.py`.
- Keep diffs small and focused.
- Avoid speculative abstractions and broad refactors.
- Do not mix unrelated fixes in one change.
- Preserve current read-only posture unless explicitly asked to change it.
- If command behavior, UX, or examples change, update `README.md`.
- If a new top-level documentation area is added, or an existing documentation layer changes role, update `docs/index.md` in the same workstream.
- If repository-specific terminology changes or important new local terms appear, update `docs/glossary.md` in the same workstream.
- If repository documentation templates change or new canonical templates are added, update `docs/templates/README.md` in the same workstream.
- If command-to-code mappings, major module responsibilities, or common structural entry points change, update `docs/architecture/README.md` in the same workstream.

## Verification checklist

Before declaring a code task complete, run the relevant checks.

Minimum expected verification for most code changes:

```bash
uv run pytest -v
uv run superset-cli --help
uv build
```

Also run the most specific targeted test(s) for the area you changed, for example:

```bash
uv run pytest tests/test_cli.py -v
uv run pytest tests/test_auth.py -v
```

If you changed CLI behavior, include at least one manual command smoke check.

## Live Superset, auth, and browser safety

Live verification is allowed, but guarded.

- Prefer local tests, mocks, and fixtures first.
- Use a real Superset instance only when needed for validation.
- Keep all live-instance actions read-only unless the user explicitly authorizes otherwise.
- Log the exact commands used for live verification.
- Announce browser-based login before launching it.
- Treat browser profiles, cookies, and `storage-state.json` as sensitive.
- Never commit credentials, auth state, browser profiles, or secrets.
- Use `/tmp` for temporary files and scratch artifacts.

## Ask-first boundaries

Ask before:
- adding or changing dependencies
- changing CLI defaults or JSON output contracts
- changing packaging, build, or `devenv` behavior
- expanding from read-only into write-capable Superset operations
- making broad architectural refactors
- running live verification that goes beyond minimal read-only checks

## Never do these things

- never fabricate results
- never claim tests passed without running them
- never claim a file contains something you did not re-read
- never remove tests or checks to make the suite pass
- never commit secrets, auth state, or browser profile data
- never use `git push`
- never create a pull request or merge request
- never perform destructive or write actions against Superset without explicit user instruction

## Definition of done

A task is not done until all relevant items below are true:

- a written plan exists for any non-trivial change
- the plan ends with a `Decision follow-up` section
- failing tests were written first
- implementation is minimal and scoped
- targeted tests pass
- `uv run pytest -v` passes for code changes
- relevant smoke checks were run
- docs were updated if behavior or workflow changed
- `docs/index.md` was updated if top-level documentation areas or doc roles changed
- `docs/architecture/README.md` was updated if structural mappings or module responsibilities changed
- decision records were added or updated if durable technical choices changed
- the final report includes:
  - files changed
  - commands run
  - actual verification results
  - consulted decision records, or an explicit statement that none were relevant
  - any remaining risks or unverified areas

## When stuck

If progress stalls:
- stop and summarize what is known
- identify the exact uncertainty
- research or inspect the narrow missing piece
- prefer a smaller verified change over a larger speculative one
- ask the user when a decision affects scope, contract, or risk
