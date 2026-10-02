# 0011: Build and publish releases through PyPI Trusted Publishing

- Status: accepted
- Date: 2026-10-02
- Related: `0007-superset-cli-product-and-package-name.md`, `../plans/2026-10-02-pypi-release.md`, `../../.github/workflows/publish.yml`, `../../tests/test_release_workflow.py`, `../../README.md`

## Context

Users should not need a Git checkout or repository authentication to install the CLI.
The same code is mirrored in the user's own organization and a company repository. Public contributions
must not execute on shared self-hosted infrastructure or gain publishing credentials.

## Decision

Distribute the existing Python package through PyPI. Use GitHub-hosted runners for
builds and publishing, with commit-pinned actions. A published GitHub release must
have a tag exactly matching `v` plus the package version. Test and build wheel and
sdist artifacts in an unprivileged job, then install-check both outside the project.
A separate publishing job only downloads those artifacts and invokes the PyPA action.
Only that job receives `id-token: write`, using PyPI Trusted Publishing and the `pypi`
GitHub environment. Require reviewer approval and release-tag protection before use.
Manual workflow dispatch builds but cannot publish. Configure the Trusted Publisher
only for `RobinOnHisOwn/superset_cli`, the user-confirmed canonical upstream owned by
the `RobinOnHisOwn` organization. The company repository is a mirror, not a separate
publishing source. Package source/issues URLs point to this canonical upstream.
The user selected the MIT license with copyright holder Robin Rittsteiger.
Include `LICENSE` in wheel and source distributions and declare SPDX expression
`MIT` in package metadata.

## Consequences

Users can install with uv or pipx independently of the source checkout. No long-lived
PyPI secret is needed. Release publishing requires human setup on GitHub and PyPI.
The user confirmed permission to publish all repository content, including
employer-related contributions. Public visibility, sensitive-history review,
organization runner isolation and publishing-service setup remain unresolved;
this workflow does not make the repository public or publish a package by itself. Full end-to-end publishing is unverified until configured
and a release is intentionally approved. The same PyPI version cannot be replaced.

## Alternatives considered

### Install directly from a private Git repository

Requires Git authentication and couples user installation to source hosting.

### Use shared self-hosted runners

Untrusted public contributions can compromise persistent runners and adjacent jobs.

### Publish from the build job with an API token

Exposes publishing privilege to build/test code and introduces a long-lived secret.

### Add standalone executables or a second package registry

Adds platform-specific release maintenance without an established user need.

## References

- [PyPA publishing guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [GitHub self-hosted runner access](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access)
