from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app

runner = CliRunner()


def test_help_advertises_allow_write_safety() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Superset CLI" in result.stdout
    assert "--allow-write" in result.stdout


def test_instances_list_defaults_to_human_output(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    result = runner.invoke(app, ["--config", str(config_path), "instances", "list"])

    assert result.exit_code == 0
    assert "No instances configured." in result.stdout


def test_instances_list_supports_json_output(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    result = runner.invoke(app, ["--config", str(config_path), "instances", "list", "--json"])

    assert result.exit_code == 0
    assert result.stdout.strip() == '{"instances":[]}'


def test_instances_list_shows_configured_instances(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"],
    )

    result = runner.invoke(app, ["--config", str(config_path), "instances", "list"])

    assert result.exit_code == 0
    assert "prod: https://superset.example.com" in result.stdout
