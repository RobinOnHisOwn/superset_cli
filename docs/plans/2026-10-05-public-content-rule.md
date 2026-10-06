# Public repository content rule

**Date:** 2026-10-05

## Goal

Keep employer- and customer-specific details out of the public repository and source distribution.

## Planned changes

1. Before publication, rewrite Git history with `git filter-repo --sensitive-data-removal`. Replace real company names and hostnames in file contents and commit messages with `Example Corp` and reserved `example.com` hosts, and map the work email on merge commits to the maintainer's personal address. Keep the replacement rules outside the repository so the original names are never committed.
2. Add a `Public repository content` section to `AGENTS.md` so later docs, tickets, tests, and commit messages use the example company and never quote real instance data.

## Verification

- Case-insensitive search of every rewritten commit (contents, messages, author and committer identities) finds no original company references.
- A tree diff against the pre-rewrite `main` shows changes only in the three affected docs.
- Gitleaks over the rewritten history reports no leaks.
- `uv run pytest -v`, `uv run superset-cli --help`, `uv build`.

## Decision follow-up

No durable decision change. The rule is recorded in `AGENTS.md`.
