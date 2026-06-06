import json
from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import NotFoundError
from fakes import FakeSupersetClient

runner = CliRunner()


# --- dashboards embedded ---


def test_dashboards_embedded_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "dashboards", "embedded", "prod", "7", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["uuid"] == "abc-123"


def test_dashboards_embedded_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "dashboards", "embedded", "prod", "7", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "UUID: abc-123" in result.stdout
    assert "Allowed domains: example.com" in result.stdout


def test_dashboards_embedded_not_found(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NF(FakeSupersetClient):
        def get_dashboard_embedded(self, id_or_slug: str) -> dict:
            raise NotFoundError("Resource not found: /api/v1/dashboard/99/embedded")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NF)
    result = runner.invoke(app, ["--config", str(config_path), "dashboards", "embedded", "prod", "99", "--state-dir", str(state_dir)])
    assert result.exit_code == 1
    assert "Resource not found" in result.stdout


# --- permalinks resolve ---


def test_permalinks_resolve_unsupported_kind(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "permalinks", "resolve", "prod", "weird", "abc", "--state-dir", str(state_dir)])
    assert result.exit_code == 1
    assert "Unsupported permalink kind 'weird'" in result.stdout


def test_permalinks_resolve_dashboard_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "permalinks", "resolve", "prod", "dashboard", "abc", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["url"] == "/dashboard/p/abc"


def test_permalinks_resolve_explore_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "permalinks", "resolve", "prod", "explore", "xyz", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "Kind: explore" in result.stdout
    assert "Key: xyz" in result.stdout


def test_permalinks_resolve_not_found(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NF(FakeSupersetClient):
        def get_permalink(self, kind: str, key: str) -> dict:
            raise NotFoundError("Resource not found: permalink")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NF)
    result = runner.invoke(app, ["--config", str(config_path), "permalinks", "resolve", "prod", "dashboard", "missing", "--state-dir", str(state_dir)])
    assert result.exit_code == 1
    assert "Resource not found" in result.stdout


# --- datasets related ---


def test_datasets_related_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "datasets", "related", "prod", "21", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["charts"]["count"] == 1


def test_datasets_related_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "datasets", "related", "prod", "21", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "Charts: 1" in result.stdout
    assert "Revenue by Month" in result.stdout
    assert "Dashboards: 1" in result.stdout


def test_datasets_related_not_found(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NF(FakeSupersetClient):
        def get_dataset_related_objects(self, id_or_uuid: str) -> dict:
            raise NotFoundError("Resource not found: /api/v1/dataset/99/related_objects")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NF)
    result = runner.invoke(app, ["--config", str(config_path), "datasets", "related", "prod", "99", "--state-dir", str(state_dir)])
    assert result.exit_code == 1
    assert "Resource not found" in result.stdout


# --- datasources column-values ---


def test_datasources_column_values_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "datasources", "column-values", "prod", "table", "21", "country", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["result"] == ["a", "b", "c"]


def test_datasources_column_values_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "datasources", "column-values", "prod", "table", "21", "country", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "a\nb\nc" in result.stdout


def test_datasources_column_values_empty(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class Empty(FakeSupersetClient):
        def get_datasource_column_values(self, datasource_type: str, datasource_id: str, column: str) -> dict:
            return {"result": []}

    monkeypatch.setattr("superset_cli.cli.SupersetClient", Empty)
    result = runner.invoke(app, ["--config", str(config_path), "datasources", "column-values", "prod", "table", "21", "country", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "No values returned." in result.stdout


def test_datasources_column_values_not_found(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NF(FakeSupersetClient):
        def get_datasource_column_values(self, datasource_type: str, datasource_id: str, column: str) -> dict:
            raise NotFoundError("Resource not found")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NF)
    result = runner.invoke(app, ["--config", str(config_path), "datasources", "column-values", "prod", "table", "99", "country", "--state-dir", str(state_dir)])
    assert result.exit_code == 1
    assert "Resource not found" in result.stdout
