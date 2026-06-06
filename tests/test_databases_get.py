import json
from pathlib import Path

import httpx
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import NotFoundError
from fakes import FakeSupersetClient

runner = CliRunner()


def test_databases_get_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "ghost", "31", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_databases_get_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"],
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_databases_get_returns_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(state_dir), "--json"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(
        {"id": 31, "database_name": "analytics", "backend": "snowflake"},
        separators=(",", ":"),
    )


def test_databases_get_returns_human_readable(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "ID: 31" in result.stdout
    assert "Name: analytics" in result.stdout
    assert "Backend: snowflake" in result.stdout


def test_databases_get_not_found_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NotFoundFake(FakeSupersetClient):
        def get_database(self, pk: str) -> dict:
            raise NotFoundError("Resource not found: /api/v1/database/99")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NotFoundFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "99", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Resource not found" in result.stdout


def test_databases_get_network_error_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NetworkErrorFake(FakeSupersetClient):
        def get_database(self, pk: str) -> dict:
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NetworkErrorFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Network error" in result.stdout


def test_databases_get_closes_client(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[FakeSupersetClient] = []

    class CapturingFake(FakeSupersetClient):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingFake)

    runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert captured[0].closed
