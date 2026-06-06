import json
from pathlib import Path

import httpx
from typer.testing import CliRunner

from superset_cli.cli import app
from fakes import FakeSupersetClient

runner = CliRunner()


def test_databases_list_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "list", "ghost", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_databases_list_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"],
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "list", "prod", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_databases_list_returns_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "list", "prod", "--state-dir", str(state_dir), "--json"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(
        {
            "count": 2,
            "result": [
                {"id": 31, "database_name": "analytics", "backend": "snowflake"},
                {"id": 32, "database_name": "warehouse", "backend": "postgresql"},
            ],
        },
        separators=(",", ":"),
    )


def test_databases_list_network_error_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NetworkErrorFake(FakeSupersetClient):
        def list_databases(self, *, page=None, page_size=None):
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NetworkErrorFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "list", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Network error" in result.stdout


def test_databases_list_closes_client(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[FakeSupersetClient] = []

    class CapturingFake(FakeSupersetClient):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "list", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert captured[0].closed


def test_databases_list_accepts_page_flags(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "list", "prod",
            "--state-dir", str(state_dir), "--page", "0", "--page-size", "10",
        ],
    )

    assert result.exit_code == 0


def test_databases_list_forwards_page_to_client(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[dict] = []

    class CapturingFake(FakeSupersetClient):
        def list_databases(self, *, page=None, page_size=None):
            captured.append({"page": page, "page_size": page_size})
            return super().list_databases(page=page, page_size=page_size)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingFake)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "list", "prod",
            "--state-dir", str(state_dir), "--page", "0", "--page-size", "25",
        ],
    )

    assert result.exit_code == 0
    assert captured[0] == {"page": 0, "page_size": 25}


def test_databases_list_empty_returns_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class EmptyFake(FakeSupersetClient):
        def list_databases(self, *, page=None, page_size=None):
            return {"count": 0, "result": []}

    monkeypatch.setattr("superset_cli.cli.SupersetClient", EmptyFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "list", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "No databases found." in result.stdout


def test_databases_list_returns_human_readable(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "list", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "31: analytics (backend=snowflake)" in result.stdout
    assert "32: warehouse (backend=postgresql)" in result.stdout


def test_databases_list_json_shape_unchanged_with_pagination(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "list", "prod",
            "--state-dir", str(state_dir), "--json", "--page", "0", "--page-size", "2",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(
        {
            "count": 2,
            "result": [
                {"id": 31, "database_name": "analytics", "backend": "snowflake"},
                {"id": 32, "database_name": "warehouse", "backend": "postgresql"},
            ],
        },
        separators=(",", ":"),
    )
