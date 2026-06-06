from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_envrc_configures_direnv_for_devenv() -> None:
    envrc_path = REPO_ROOT / ".envrc"

    assert envrc_path.exists()

    content = envrc_path.read_text()
    assert 'eval "$(devenv direnvrc)"' in content
    assert "use devenv" in content


def test_pyproject_exposes_superset_cli_command() -> None:
    pyproject_path = REPO_ROOT / "pyproject.toml"

    assert pyproject_path.exists()

    content = pyproject_path.read_text()
    assert 'name = "superset-cli"' in content
    assert 'superset-cli = "superset_cli.main:main"' in content
    assert 'superset-agent' not in content
    assert 'superset_agent_cli.main:main' not in content



def test_ci_workflow_runs_expected_uv_checks() -> None:
    workflow_path = REPO_ROOT / ".github/workflows/ci.yml"

    assert workflow_path.exists()

    content = workflow_path.read_text()
    workflow = yaml.safe_load(content)

    assert "pull_request" in workflow["on"]
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"] == ["3.12", "3.13"]
    assert "uv sync --locked --group dev" in content
    assert "uv run pytest -v" in content
    assert "uv run superset-cli --help" in content
    assert "uv build" in content
    assert "uv run --isolated --no-project --with dist/*.whl superset-cli --help" in content
