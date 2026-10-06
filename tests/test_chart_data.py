import json

import pytest
from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import NotFoundError
from fakes import FakeSupersetClient

runner = CliRunner()


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("queries, error", [
    ([{"status": "success", "data": [{"value": 0}], "rowcount": 1}], None),
    ([{"status": "success", "data": [{"value": None}], "rowcount": 1}], None),
    ([{"status": "failed", "error": "Invalid metric", "data": []}], "Invalid metric"),
    ([{"status": "failed", "data": []}], "chart queries failed"),
    ([{"status": "success", "data": [], "rowcount": 0}], "chart returned 0 rows"),
    ([], "chart returned 0 rows"),
    ([{"status": "success", "data": [{"value": 7}]}, {"status": "success", "data": []}], None),
    ([{"status": "failed", "data": []}, {"status": "success", "data": [{"value": 7}]}], None),
    ([{"status": "success", "data": []}, {"status": "failed", "data": [{"value": 7}]}], "chart returned 0 rows"),
])
def test_chart_data_exit_contract(monkeypatch, instance_setup, as_json, queries, error):
    config_path, state_dir = instance_setup
    payload = {"result": queries}
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    monkeypatch.setattr(FakeSupersetClient, "get_chart_data", lambda self, pk: payload)
    args = ["--config", str(config_path), "charts", "data", "prod", "10", "--state-dir", str(state_dir)]
    result = runner.invoke(app, args + (["--json"] if as_json else []))
    assert result.exit_code == (1 if error else 0)
    if error:
        assert error in result.stderr
    else:
        assert result.stderr == ""
    if as_json:
        assert json.loads(result.stdout) == payload
    else:
        assert f"Queries: {len(queries)}" in result.stdout


@pytest.mark.parametrize("queries, expected", [
    ([{"colnames": ["__timestamp", "value"], "data": [{"__timestamp": 0, "value": 42}]}],
     "__timestamp,value\n1970-01-01T00:00:00+00:00,42\n"),
    ([{"colnames": ["name", "value"], "data": [{"name": "a,b", "value": None}]}],
     'name,value\n"a,b",\n'),
    ([{"colnames": ["value"], "data": [{"value": 0}]}, {"colnames": ["value"], "data": [{"value": 2}]}],
     "value\n0\n\nvalue\n2\n"),
])
def test_chart_data_csv(monkeypatch, instance_setup, queries, expected):
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    monkeypatch.setattr(FakeSupersetClient, "get_chart_data", lambda self, pk: {"result": queries})
    result = runner.invoke(app, ["--config", str(config_path), "charts", "data", "prod", "10",
                                 "--state-dir", str(state_dir), "--csv"])
    assert result.exit_code == 0
    assert result.stdout == expected


def test_chart_data_csv_json_conflict(monkeypatch, instance_setup):
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "charts", "data", "prod", "10",
                                 "--state-dir", str(state_dir), "--csv", "--json"])
    assert result.exit_code == 2
    assert "--csv and --json" in result.stderr



def test_charts_data_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")
    result = runner.invoke(app, ["--config", str(config_path), "charts", "data", "ghost", "10", "--state-dir", str(tmp_path / "state")])
    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_charts_data_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(app, ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"])
    result = runner.invoke(app, ["--config", str(config_path), "charts", "data", "prod", "10", "--state-dir", str(tmp_path / "state")])
    assert result.exit_code == 1
    assert "No saved auth state" in result.stdout


def test_charts_data_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "charts", "data", "prod", "10", "--state-dir", str(state_dir), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["result"][0]["rowcount"] == 2


def test_charts_data_human(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    result = runner.invoke(app, ["--config", str(config_path), "charts", "data", "prod", "10", "--state-dir", str(state_dir)])
    assert result.exit_code == 0
    assert "Queries: 1" in result.stdout
    assert "rows=2 columns=month,revenue" in result.stdout


def test_charts_data_not_found(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NF(FakeSupersetClient):
        def get_chart_data(self, pk: str) -> dict:
            raise NotFoundError("Resource not found: /api/v1/chart/99/data/")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NF)
    result = runner.invoke(app, ["--config", str(config_path), "charts", "data", "prod", "99", "--state-dir", str(state_dir)])
    assert result.exit_code == 1
    assert "Resource not found" in result.stdout
