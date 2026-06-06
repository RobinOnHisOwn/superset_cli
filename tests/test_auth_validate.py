import json
from pathlib import Path

import httpx
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import AuthExpiredError
from fakes import FakeSupersetClient

runner = CliRunner()


def test_auth_validate_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"],
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "validate", "prod", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_auth_validate_returns_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "validate", "prod", "--state-dir", str(state_dir), "--json"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(
        {
            "instance": "prod",
            "base_url": "https://superset.example.com",
            "authenticated": True,
            "user": {
                "id": 3,
                "username": "agent@example.com",
                "first_name": "Superset",
                "last_name": "Agent",
            },
        },
        separators=(",", ":"),
    )


def test_auth_validate_auth_expired_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class ExpiredFake(FakeSupersetClient):
        def get_current_user(self) -> dict:
            raise AuthExpiredError("Session expired or invalid. Run 'auth login' to re-authenticate.")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", ExpiredFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "validate", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Session expired" in result.stdout


def test_auth_validate_returns_human_readable(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "validate", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "Authenticated: True" in result.stdout
    assert "User: agent@example.com" in result.stdout


def test_auth_validate_unknown_instance_prints_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "validate", "ghost", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_auth_validate_network_error_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NetworkErrorFake(FakeSupersetClient):
        def get_current_user(self) -> dict:
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NetworkErrorFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "validate", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Network error" in result.stdout


def test_auth_validate_closes_client(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[FakeSupersetClient] = []

    class CapturingFake(FakeSupersetClient):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingFake)

    runner.invoke(
        app,
        ["--config", str(config_path), "auth", "validate", "prod", "--state-dir", str(state_dir)],
    )

    assert captured[0].closed
