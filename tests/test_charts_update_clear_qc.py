import json
from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app

runner = CliRunner()


def _setup(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("instances:\n  - name: prod\n    base_url: https://superset.example.com\n")
    d = tmp_path / "state" / "prod"
    d.mkdir(parents=True, exist_ok=True)
    (d / "storage-state.json").write_text(json.dumps({"cookies": [], "origins": []}))
    return config_path, tmp_path / "state"


def _client_recording(captured):
    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def update_chart(self, pk, payload):
            captured["pk"] = pk
            captured["payload"] = payload
            return {"id": int(pk)}

    return Client


def test_clear_query_context_standalone_sets_null(monkeypatch, tmp_path):
    config_path, state_dir = _setup(tmp_path)
    captured: dict = {}
    monkeypatch.setattr("superset_cli.cli.SupersetClient", _client_recording(captured))
    result = runner.invoke(
        app,
        ["--config", str(config_path), "charts", "update", "prod", "7075",
         "--clear-query-context", "--allow-write", "--state-dir", str(state_dir)],
    )
    assert result.exit_code == 0
    assert captured["payload"] == {"query_context": None}


def test_clear_query_context_merges_with_body(monkeypatch, tmp_path):
    config_path, state_dir = _setup(tmp_path)
    captured: dict = {}
    monkeypatch.setattr("superset_cli.cli.SupersetClient", _client_recording(captured))
    result = runner.invoke(
        app,
        ["--config", str(config_path), "charts", "update", "prod", "7075",
         "--body", json.dumps({"params": "{}"}), "--clear-query-context",
         "--allow-write", "--state-dir", str(state_dir)],
    )
    assert result.exit_code == 0
    assert captured["payload"]["params"] == "{}"
    assert captured["payload"]["query_context"] is None


def test_clear_query_context_requires_allow_write(monkeypatch, tmp_path):
    config_path, state_dir = _setup(tmp_path)
    monkeypatch.setattr("superset_cli.cli.SupersetClient", _client_recording({}))
    result = runner.invoke(
        app,
        ["--config", str(config_path), "charts", "update", "prod", "7075",
         "--clear-query-context", "--state-dir", str(state_dir)],
    )
    assert result.exit_code != 0
