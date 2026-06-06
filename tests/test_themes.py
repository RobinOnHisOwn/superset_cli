import json
from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import NotFoundError
from fakes import FakeSupersetClient

runner = CliRunner()


def test_themes_list_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")
    result = runner.invoke(app, ["--config", str(config_path), "themes", "list", "ghost", "--state-dir", str(tmp_path / "state")])
    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_themes_list_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(app, ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"])
    result = runner.invoke(app, ["--config", str(config_path), "themes", "list", "prod", "--state-dir", str(tmp_path / "state")])
    assert result.exit_code == 1
    assert "No saved auth state" in result.stdout


def test_themes_list_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "themes", "list", "prod", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["result"][0]["theme_name"] == "Default"


def test_themes_list_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "themes", "list", "prod", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "1: Default" in result.stdout


def test_themes_list_empty(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class Empty(FakeSupersetClient):
        def list_themes(self, **kwargs) -> dict:
            return {"count": 0, "result": []}

    monkeypatch.setattr("superset_cli.cli.SupersetClient", Empty)
    result = runner.invoke(app, ["--config", str(config_path), "themes", "list", "prod", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "No themes found." in result.stdout


def test_themes_get_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "themes", "get", "prod", "1", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["theme_name"] == "Default"


def test_themes_get_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "themes", "get", "prod", "1", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "Name: Default" in result.stdout


def test_themes_get_not_found(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NF(FakeSupersetClient):
        def get_theme(self, pk: str) -> dict:
            raise NotFoundError("Resource not found: /api/v1/theme/99")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NF)
    result = runner.invoke(app, ["--config", str(config_path), "themes", "get", "prod", "99", "--state-dir", str(state_dir)])
    assert result.exit_code == 1
    assert "Resource not found" in result.stdout
