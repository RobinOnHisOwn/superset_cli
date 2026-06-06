# Evaluate Markdown docs verification

## Status

Research only. No code changes in this plan; one possible follow-up code ticket recommended.

## Options surveyed

### A. No automated verification

- Pros: zero dependencies, zero CI cost.
- Cons: stale links and broken in-doc references accumulate silently. The doc tree is growing (`docs/plans/`, `docs/decisions/`, `docs/architecture/`, `docs/tickets/{todo,in-progress,done}`) and now has interlinking conventions.

### B. `markdownlint-cli2` (npm)

- Catches style issues (heading levels, trailing whitespace, etc.).
- Cons: introduces a Node toolchain; doesn't validate links.

### C. `lychee` (Rust, single binary)

- Validates internal and external links in Markdown.
- Cons: external Rust binary; needs network access for external links.

### D. Tiny in-repo Python check

- A small script under `tests/` or `scripts/` that walks `docs/**/*.md`, parses Markdown links, and asserts that every relative link resolves to a file in the repo. Skips external HTTP(S) links.
- Pros: no new dependency (stdlib only); fast; integrates with the existing `uv run pytest` flow as a test; covers the most common rot pattern (a moved or deleted doc).
- Cons: doesn't catch external link rot.

## Recommendation

Option **D**: add a lightweight test that walks `docs/**/*.md` and verifies that every relative Markdown link resolves to an existing path. Skip external links. This is the cheapest change that catches the failure mode the doc tree is most likely to hit (renames and deletions).

Where to document the new check:

- The check itself is a test, so it shows up in `tests/test_repo_files.py` or a new `tests/test_docs_links.py`. Either is fine; a new file is clearer.
- No new top-level documentation map entry is needed — it's implementation detail of the test suite.
- No new decision record needed unless we later adopt one of the heavier tools.

## Follow-up ticket

`2026-06-06-docs-relative-link-check.md` (created in `todo/`).

## Decision follow-up

No durable decision change. If the heavier options A or B are adopted later, that should be captured in a decision record at the time.
