from pathlib import Path

from typer.testing import CliRunner

from superset_agent_cli.cli import app

runner = CliRunner()


def _add(config_path: Path, name: str, url: str) -> None:
    runner.invoke(app, ["--config", str(config_path), "instances", "add", name, url])


def _make_auth_state(state_dir: Path, name: str) -> Path:
    instance_dir = state_dir / name
    instance_dir.mkdir(parents=True, exist_ok=True)
    (instance_dir / "storage-state.json").write_text('{"cookies":[],"origins":[]}')
    return instance_dir


def test_auth_logout_unknown_instance_exits_with_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "logout", "ghost", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_auth_logout_absent_auth_state_exits_with_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _add(config_path, "prod", "https://superset.example.com")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "logout", "prod", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout
    assert "Nothing to remove" in result.stdout


def test_auth_logout_removes_auth_state_dir(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add(config_path, "prod", "https://superset.example.com")
    instance_dir = _make_auth_state(state_dir, "prod")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "logout", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert not instance_dir.exists()


def test_auth_logout_human_output(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add(config_path, "prod", "https://superset.example.com")
    _make_auth_state(state_dir, "prod")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "logout", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "Removed auth state for instance 'prod'." in result.stdout


def test_auth_logout_json_output(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add(config_path, "prod", "https://superset.example.com")
    _make_auth_state(state_dir, "prod")

    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "auth",
            "logout",
            "prod",
            "--state-dir",
            str(state_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == '{"removed_auth_state":"prod"}'


def test_auth_logout_does_not_affect_other_instances(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add(config_path, "prod", "https://prod.example.com")
    _add(config_path, "staging", "https://staging.example.com")
    _make_auth_state(state_dir, "prod")
    staging_dir = _make_auth_state(state_dir, "staging")

    runner.invoke(
        app,
        ["--config", str(config_path), "auth", "logout", "prod", "--state-dir", str(state_dir)],
    )

    assert staging_dir.exists(), "staging auth state must not be touched"
