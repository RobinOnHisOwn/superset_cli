from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.config import load_config

runner = CliRunner()


def test_instances_add_persists_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "instances",
            "add",
            "prod",
            "https://superset.example.com",
        ],
    )

    assert result.exit_code == 0
    assert "Saved instance 'prod'." in result.stdout

    config = load_config(config_path)
    assert len(config.instances) == 1
    assert config.instances[0].name == "prod"
    assert config.instances[0].base_url == "https://superset.example.com"


def test_instances_add_is_visible_in_json_list(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "instances",
            "add",
            "prod",
            "https://superset.example.com",
        ],
    )

    result = runner.invoke(app, ["--config", str(config_path), "instances", "list", "--json"])

    assert result.exit_code == 0
    assert result.stdout.strip() == (
        '{"instances":[{"name":"prod","base_url":"https://superset.example.com"}]}'
    )
