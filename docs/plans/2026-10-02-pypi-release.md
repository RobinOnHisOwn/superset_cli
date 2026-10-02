# Build and PyPI publishing implementation plan

**Date:** 2026-10-02

## Goal

Build tested distributions on GitHub-hosted runners and publish approved releases through PyPI Trusted Publishing.

## Verified prerequisites

- `pyproject.toml` exposes `superset-cli`, uses Hatchling, and requires Python >=3.12 (ADR 0007).
- Existing CI uses GitHub-hosted runners, uv, locked dependencies, tests, and a wheel smoke check.
- `RobinOnHisOwn/superset_cli` is private, has no detected license or environments, and Actions uses read-only default token permissions.
- PyPI's project JSON endpoint returns 404 for `superset-cli`; registration availability is not guaranteed.
- User confirmed `RobinOnHisOwn/superset_cli` as canonical upstream; GitHub verifies `RobinOnHisOwn` is an organization. The company repository remains a mirror.
- User selected MIT with copyright holder Robin Rittsteiger; current year is verified as 2026.
- User confirmed permission to publish all repository content, including employer-related contributions. This is the user's attestation, not an independent legal review.
- User reports the pending PyPI Trusted Publisher is configured for `superset-cli`, owner `RobinOnHisOwn`, repo `superset_cli`, workflow `publish.yml`, environment `pypi`. Private PyPI account settings were not independently inspected; OIDC publishing remains untested.
- Unknown: company mirror settings (API returns 404).

## Planned changes

1. Add failing workflow-contract tests and executable tag/version validation tests in `tests/test_release_workflow.py`; run them before implementation.
2. Add `.github/workflows/publish.yml`: manual build-only runs, published-release runs, locked tests, tag/version validation, wheel and sdist builds and install checks, artifact transfer, and a separate OIDC-only publishing job behind the `pypi` environment.
3. Document setup and release steps in README without claiming the package is published.
4. Record the durable distribution/security choice in ADR 0011.
5. Audit package contents and repository configuration; report blockers without changing remote state or choosing a license/owner.

## Canonical upstream follow-up

User confirmed the canonical upstream after the initial workflow implementation.
Add a failing test for package source/issues URLs, verify the failure, then add
`project.urls` pointing to `RobinOnHisOwn/superset_cli`. Update README and ADR 0011
to record the chosen upstream. Re-run focused/full tests, locked sync, CLI help,
build and wheel metadata inspection. Do not select a license or change remote settings.

## MIT license follow-up

The user selected MIT and named Robin Rittsteiger as copyright holder. Use the
verified current year, 2026. Add a failing test for the license file, copyright
notice and `project.license`/`project.license-files` metadata; verify failure before
adding `LICENSE` and the metadata. Update README and ADR 0011. Re-run focused/full
tests, locked sync, help, and build. Inspect both archives for MIT metadata and the
exact license text. License selection does not itself establish employer approval.

## Verification

- `uv run pytest tests/test_release_workflow.py -v` (red, then green).
- `uv run pytest -v`, `uv run superset-cli --help`, `uv build`.
- Install/smoke-check wheel and sdist outside the checkout; inspect distribution metadata and contents.
- Validate workflow syntax with actionlint if available; inspect GitHub Actions permissions, environments, runners and protection settings read-only.
- Public release still requires a human-owned license, source/history security review, canonical repository choice, protected `pypi` environment, and PyPI Trusted Publisher setup. No live publishing test is authorized.

## Verification results and release audit

- New workflow tests failed because `publish.yml` was absent, then all four passed.
- `uv sync --locked --group dev`: passed; no dependency or lockfile changes.
- `uv run pytest -v`: 466 passed on macOS / Python 3.13.
- `uv run superset-cli --help` and `uv build`: passed.
- Wheel and sdist installed in isolated uv environments and ran `superset-cli --help` from `/tmp`.
- `actionlint .github/workflows/ci.yml .github/workflows/publish.yml`: passed.
- `git diff --check`: passed.
- Redacted Gitleaks scans of all locally available Git refs (11 commits) and current files: no leaks found. Not a guarantee against sensitive business content or histories unavailable locally.
- The specdocs validator reported an existing error in `docs/architecture/README.md` (filename does not match its plan naming pattern). The tool is bound to the original checkout, so it did not validate this worktree's new documents.

### Blockers before public release

1. **Canonical upstream and publishing authorization confirmed.** User confirmed `RobinOnHisOwn/superset_cli`, owned by the `RobinOnHisOwn` organization, and permission to publish all content, including employer-related contributions.
2. **License implemented locally.** User selected MIT and copyright holder Robin Rittsteiger. `LICENSE` and SPDX package metadata are added; both wheel and sdist contain the exact license and declare `License-Expression: MIT`. Changes have not yet been integrated into the canonical default branch or published, so remote license detection has not changed.
3. **GitHub setup partially completed by the user.** The `pypi` environment exists. Live API verification confirms selected deployment policies contain only tags matching `v*`; no branches are allowed. No required reviewer is configured. Required reviewers on Free/Pro/Team plans are available only for public repositories; configure the sole maintainer as reviewer after making the reviewed repository public, leaving prevent-self-review disabled. The repo remains private. User reports the matching pending PyPI Trusted Publisher is configured. PyPI account configuration is not inspectable with the available GitHub credentials; no upload has been attempted.
4. **Organization runner isolation user-confirmed; branch/tag protection unverified.** The repository runner API previously listed zero runners; this does not establish organization-level isolation. Organization runner and runner-group APIs now return 403: credentials lack `admin:org` scope or equivalent runner permissions. User reports runner-group isolation is configured. The repeated API check still returns 403, so this is user-confirmed rather than independently inspected. Keep public-repository access disabled and restrict groups to explicitly selected private repositories. Branch/ruleset APIs previously returned 403 requiring an upgraded plan or public visibility; protection remains unverified.
5. **Security review incomplete.** GitHub secret scanning is disabled on the canonical repo. Automated scans found no leaks but do not detect all internal/business information. Inspect history before publication and enable applicable GitHub protections. The company mirror API returns 404 (not proof that the repository is absent).

### Non-blocking package observations and remaining verification

- The wheel contains the seven application modules and distribution metadata; no runtime dependency on the repository or devenv was found by source-path checks. Both artifact install smoke checks passed.
- The sdist includes docs, tests, scripts and `.envrc`; review those as public release content. No saved auth state, browser profile, private-key file, or devenv directory was identified in its member listing.
- Canonical source/issues URLs are implemented and verified in wheel metadata.
- Local artifact checks ran on macOS/Python 3.13, not the workflow's Ubuntu/Python 3.12. GitHub execution, environment approval, OIDC exchange and actual PyPI upload remain untested. Browser-cookie login and Windows/Linux browser access were not tested live.
- Existing CI is separate; the release job repeats tests on Python 3.12. Maintainers should require the existing Python 3.12/3.13 matrix CI to pass on the reviewed release commit.
- MIT follow-up: the new license test failed with missing license metadata, then all six focused tests and all 468 suite tests passed. Locked sync, CLI help, build, archive metadata/license checks and `git diff --check` passed.
- The user configured runner isolation and the `pypi` environment remotely; the agent only inspected those settings. No agent-driven remote changes, package dependency/source behavior changes, pushes, or publication were performed. The user subsequently authorized staging and a local commit of these eight release-related files.

## Decision follow-up

Decision record update required: `docs/decisions/0011-pypi-release-publishing.md`.
