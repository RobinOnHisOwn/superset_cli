# Make installed CLI capabilities match documented workflows

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `pyproject.toml`, `README.md`, `docs/decisions/0011-pypi-release-publishing.md`, `docs/tickets/done/2026-08-26-csrf-write-requests.md`, `docs/tickets/todo/2026-10-06-refresh-companion-skill-recipes.md`

## Context

Verified during a local installation audit: both the installed package and checkout declared version `0.1.0`, but only the checkout contained CSRF handling, validated browser fallback, the custom `api` command, and `--clear-query-context`. The installed executable did not support `--version`. Agents repeatedly recreated fixes already present in source. The executable also existed in the user's local binary directory but was absent from the agent's PATH.

Current publication and upgrade state must be rechecked before implementation; this is a distribution/provenance problem, not a request to reimplement existing features.

## Definition of done

- [ ] Inspect the latest published artifact and document which capabilities it actually provides.
- [ ] Give feature-bearing releases distinct versions; expose the running package version through a tested CLI command or option.
- [ ] Document installation provenance, PATH discovery, and upgrades for supported installation methods without installing duplicate copies unnecessarily.
- [ ] Add a companion-skill preflight that checks the selected executable and required command capabilities, rather than trusting a version string alone.
- [ ] Build an artifact and verify in an isolated environment that the documented API, CSRF, auth-validation, and chart-update capabilities are present; test upgrading an older installation.
- [ ] Preserve auth/config state during upgrade; obtain explicit authorization before any publication.

## Notes

Prioritize this before implementing new operational helpers. Packaging changes require the repository's ask-first approval. No release or live Superset mutation is authorized by this ticket.
