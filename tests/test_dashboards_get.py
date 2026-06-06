import json
from pathlib import Path

import httpx
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import NotFoundError
from fakes import FakeSupersetClient

runner = CliRunner()


def test_dashboards_get_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "dashboards", "get", "ghost", "7", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_dashboards_get_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"],
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "dashboards", "get", "prod", "7", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_dashboards_get_returns_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "dashboards", "get", "prod", "7", "--state-dir", str(state_dir), "--json"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(
        {"id": 7, "slug": "revenue", "dashboard_title": "Revenue", "published": True},
        separators=(",", ":"),
    )


def test_dashboards_get_returns_human_readable(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "dashboards", "get", "prod", "7", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "ID: 7" in result.stdout
    assert "Title: Revenue" in result.stdout
    assert "Slug: revenue" in result.stdout
    assert "Published: True" in result.stdout


def test_dashboards_get_not_found_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NotFoundFake(FakeSupersetClient):
        def get_dashboard(self, id_or_slug: str) -> dict:
            raise NotFoundError("Resource not found: /api/v1/dashboard/99")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NotFoundFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "dashboards", "get", "prod", "99", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Resource not found" in result.stdout


def test_dashboards_get_network_error_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NetworkErrorFake(FakeSupersetClient):
        def get_dashboard(self, id_or_slug: str) -> dict:
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NetworkErrorFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "dashboards", "get", "prod", "7", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Network error" in result.stdout


def test_dashboards_get_closes_client(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[FakeSupersetClient] = []

    class CapturingFake(FakeSupersetClient):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingFake)

    runner.invoke(
        app,
        ["--config", str(config_path), "dashboards", "get", "prod", "7", "--state-dir", str(state_dir)],
    )

    assert captured[0].closed
