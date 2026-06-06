# Add docs relative-link check test

- Status: todo
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: `docs/plans/2026-06-06-evaluate-markdown-docs-verification.md`, `tests/`

## Context

Per the Markdown docs verification evaluation, add a lightweight in-repo test that walks `docs/**/*.md` and asserts that every relative Markdown link resolves to an existing path in the repository. External (`http://`, `https://`, `mailto:`) links are skipped.

## Definition of done

- [ ] A new test file (for example `tests/test_docs_links.py`) parses Markdown link syntax and validates relative targets against the filesystem.
- [ ] The test runs as part of `uv run pytest`.
- [ ] Any currently broken relative links are either fixed or explicitly allowlisted with a clear reason.

## Notes

Keep this stdlib-only. No new dependency.
