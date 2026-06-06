from pathlib import Path

from typer.testing import CliRunner

from superset_agent_cli.cli import app

runner = CliRunner()


def test_auth_login_requires_known_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    result = runner.invoke(app, ["--config", str(config_path), "auth", "login", "prod"])

    assert result.exit_code == 1
    assert "Unknown instance 'prod'" in result.stdout


def test_auth_login_invokes_browser_flow(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
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

    captured: dict[str, str] = {}

    def fake_login(*, base_url: str, profile_dir: Path, storage_state_path: Path) -> None:
        captured["base_url"] = base_url
        captured["profile_dir"] = str(profile_dir)
        captured["storage_state_path"] = str(storage_state_path)

    monkeypatch.setattr("superset_agent_cli.cli.login_with_browser", fake_login)

    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "auth",
            "login",
            "prod",
            "--state-dir",
            str(state_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == (
        '{"instance":"prod","base_url":"https://superset.example.com",'
        '"profile_dir":"' + str(state_dir / "prod" / "profile") + '",'
        '"storage_state_path":"' + str(state_dir / "prod" / "storage-state.json") + '"}'
    )
    assert captured == {
        "base_url": "https://superset.example.com",
        "profile_dir": str(state_dir / "prod" / "profile"),
        "storage_state_path": str(state_dir / "prod" / "storage-state.json"),
    }
