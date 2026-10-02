from pathlib import Path

import pytest
from rich.text import Text
from typer.testing import CliRunner

from superset_cli.cli import app

runner = CliRunner()


@pytest.mark.parametrize("force_color", [False, True])
def test_help_advertises_allow_write_safety(
    monkeypatch: pytest.MonkeyPatch, force_color: bool
) -> None:
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR" if force_color else "NO_COLOR", "1")
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    if force_color:
        assert "\x1b[" in result.stdout
    help_text = Text.from_ansi(result.stdout).plain
    assert "Superset CLI" in help_text
    assert "--allow-write" in help_text


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
