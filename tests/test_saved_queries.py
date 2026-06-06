import json
from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import NotFoundError
from fakes import FakeSupersetClient

runner = CliRunner()


def test_saved_queries_list_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")
    result = runner.invoke(app, ["--config", str(config_path), "saved-queries", "list", "ghost", "--state-dir", str(tmp_path / "state")])
    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_saved_queries_list_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(app, ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"])
    result = runner.invoke(app, ["--config", str(config_path), "saved-queries", "list", "prod", "--state-dir", str(tmp_path / "state")])
    assert result.exit_code == 1
    assert "No saved auth state" in result.stdout


def test_saved_queries_list_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "saved-queries", "list", "prod", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["result"][0]["label"] == "Top customers"


def test_saved_queries_list_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "saved-queries", "list", "prod", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "1: Top customers (schema=analytics)" in result.stdout


def test_saved_queries_list_empty(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class Empty(FakeSupersetClient):
        def list_saved_queries(self, **kwargs) -> dict:
            return {"count": 0, "result": []}

    monkeypatch.setattr("superset_cli.cli.SupersetClient", Empty)
    result = runner.invoke(app, ["--config", str(config_path), "saved-queries", "list", "prod", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "No saved queries found." in result.stdout


def test_saved_queries_get_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "saved-queries", "get", "prod", "1", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["label"] == "Top customers"


def test_saved_queries_get_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "saved-queries", "get", "prod", "1", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "Label: Top customers" in result.stdout


def test_saved_queries_get_not_found(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NF(FakeSupersetClient):
        def get_saved_query(self, pk: str) -> dict:
            raise NotFoundError("Resource not found: /api/v1/saved_query/99")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NF)
    result = runner.invoke(app, ["--config", str(config_path), "saved-queries", "get", "prod", "99", "--state-dir", str(state_dir)])
    assert result.exit_code == 1
    assert "Resource not found" in result.stdout
