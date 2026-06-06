import json
from pathlib import Path

from typer.testing import CliRunner

from superset_agent_cli.cli import app

runner = CliRunner()


def test_auth_status_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "status", "ghost", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_auth_status_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "instances",
            "add",
            "prod",
            "https://superset.example.com",
        ],
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "status", "prod", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_auth_status_reports_saved_state(instance_setup_with_session) -> None:
    config_path, state_dir, storage_state_path = instance_setup_with_session

    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "auth",
            "status",
            "prod",
            "--state-dir",
            str(state_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(
        {
            "instance": "prod",
            "base_url": "https://superset.example.com",
            "authenticated": True,
            "storage_state_path": str(storage_state_path),
            "cookie_count": 1,
        },
        separators=(",", ":"),
    )


def test_auth_status_returns_human_readable(instance_setup_with_session) -> None:
    config_path, state_dir, storage_state_path = instance_setup_with_session

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "status", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "Authenticated: True" in result.stdout
    assert str(storage_state_path) in result.stdout
    assert "Cookie count: 1" in result.stdout
