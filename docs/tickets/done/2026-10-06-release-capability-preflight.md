# Make installed CLI capabilities match documented workflows

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `pyproject.toml`, `README.md`, `docs/decisions/0011-pypi-release-publishing.md`, `docs/tickets/done/2026-08-26-csrf-write-requests.md`, `docs/tickets/in-progress/2026-10-06-refresh-companion-skill-recipes.md`

## Context

Verified during a local installation audit: both the installed package and checkout declared version `0.1.0`, but only the checkout contained CSRF handling, validated browser fallback, the custom `api` command, and `--clear-query-context`. The installed executable did not support `--version`. Agents repeatedly recreated fixes already present in source. The executable also existed in the user's local binary directory but was absent from the agent's PATH.

Current publication and upgrade state must be rechecked before implementation; this is a distribution/provenance problem, not a request to reimplement existing features.

## Definition of done

- [x] Inspect the latest published artifact and document which capabilities it actually provides.
- [x] Give feature-bearing releases distinct versions; expose the running package version through a tested CLI command or option.
- [x] Document installation provenance, PATH discovery, and upgrades for supported installation methods without installing duplicate copies unnecessarily.
- [x] Add a companion-skill preflight that checks the selected executable and required command capabilities, rather than trusting a version string alone.
- [x] Build an artifact and verify in an isolated environment that the documented API, CSRF, auth-validation, and chart-update capabilities are present; test upgrading an older installation.
- [x] Preserve auth/config state during upgrade; obtain explicit authorization before any publication.

## Completion evidence

Latest PyPI remains 0.1.0; its official wheel SHA-256 was verified and it includes API/CSRF/auth-validation/context clearing, unlike the stale local installation carrying the same label. Build 0.2.0 has a tested eager `--version`. Ninety isolated installed-wheel tests passed after a real official-0.1.0-to-local-0.2.0 upgrade; imports were asserted to come from the isolated wheel, and config/auth byte digests stayed unchanged. Source docs distinguish unpublished 0.2.0 capabilities and cover owner/PATH/upgrade preflight. No publication or machine-wide installation change. See [continuation evidence](../../plans/2026-10-06-autonomous-todos-continuation.md).

## Notes

Prioritize this before implementing new operational helpers. Packaging changes require the repository's ask-first approval. No release or live Superset mutation is authorized by this ticket.
