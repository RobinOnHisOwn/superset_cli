from pathlib import Path

from typer.testing import CliRunner

from superset_agent_cli.cli import app
from superset_agent_cli.config import load_config

runner = CliRunner()


def _add(config_path: Path, name: str, url: str) -> None:
    runner.invoke(app, ["--config", str(config_path), "instances", "add", name, url])


def test_instances_remove_unknown_instance_exits_with_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    result = runner.invoke(app, ["--config", str(config_path), "instances", "remove", "ghost"])

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_instances_remove_removes_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _add(config_path, "prod", "https://superset.example.com")

    result = runner.invoke(app, ["--config", str(config_path), "instances", "remove", "prod"])

    assert result.exit_code == 0
    config = load_config(config_path)
    assert config.instances == []


def test_instances_remove_human_output(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _add(config_path, "prod", "https://superset.example.com")

    result = runner.invoke(app, ["--config", str(config_path), "instances", "remove", "prod"])

    assert result.exit_code == 0
    assert "Removed instance 'prod'." in result.stdout


def test_instances_remove_json_output(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _add(config_path, "prod", "https://superset.example.com")

    result = runner.invoke(
        app, ["--config", str(config_path), "instances", "remove", "prod", "--json"]
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == '{"removed":"prod"}'


def test_instances_remove_does_not_delete_auth_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add(config_path, "prod", "https://superset.example.com")
    auth_dir = state_dir / "prod"
    auth_dir.mkdir(parents=True)
    (auth_dir / "storage-state.json").write_text('{"cookies":[],"origins":[]}')

    runner.invoke(app, ["--config", str(config_path), "instances", "remove", "prod"])

    assert auth_dir.exists(), "auth state directory must not be removed by 'instances remove'"


def test_instances_remove_leaves_other_instances_intact(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _add(config_path, "prod", "https://prod.example.com")
    _add(config_path, "staging", "https://staging.example.com")

    runner.invoke(app, ["--config", str(config_path), "instances", "remove", "prod"])

    config = load_config(config_path)
    assert len(config.instances) == 1
    assert config.instances[0].name == "staging"
