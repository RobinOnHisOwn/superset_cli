import json
from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app

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
            "earliest_cookie_expiry": None,
            "expired": False,
            "session_only": True,
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
    assert "Earliest cookie expiry: session-only" in result.stdout
    assert "Expired: False" in result.stdout


def test_auth_status_reports_expired_cookie(tmp_path: Path) -> None:
    from typer.testing import CliRunner
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    storage_state_path = state_dir / "prod" / "storage-state.json"
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    storage_state_path.write_text(json.dumps({
        "cookies": [{
            "name": "session", "value": "abc", "domain": "superset.example.com",
            "path": "/", "expires": 1000000.0,
        }],
        "origins": [],
    }))
    CliRunner().invoke(app, ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"])
    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "status", "prod", "--state-dir", str(state_dir), "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["expired"] is True
    assert payload["session_only"] is False
    assert payload["earliest_cookie_expiry"] == 1000000.0


def test_auth_status_reports_future_cookie(tmp_path: Path) -> None:
    import time
    from typer.testing import CliRunner
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    storage_state_path = state_dir / "prod" / "storage-state.json"
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    future = time.time() + 3600 * 24 * 30
    storage_state_path.write_text(json.dumps({
        "cookies": [{
            "name": "session", "value": "abc", "domain": "superset.example.com",
            "path": "/", "expires": future,
        }],
        "origins": [],
    }))
    CliRunner().invoke(app, ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"])
    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "status", "prod", "--state-dir", str(state_dir), "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["expired"] is False
    assert payload["session_only"] is False
