"""Tests for write commands.

Each command must:
  * refuse to run without --allow-write (exit 1, no client call)
  * succeed with --allow-write and forward the call to the client
  * preserve JSON output shape
"""
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fakes import FakeSupersetClient
from superset_cli.cli import app

runner = CliRunner()


def _setup(monkeypatch, instance_setup) -> tuple[Path, Path, list[FakeSupersetClient]]:
    config_path, state_dir = instance_setup
    captured: list[FakeSupersetClient] = []

    class CapturingFake(FakeSupersetClient):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingFake)
    return config_path, state_dir, captured


# Each entry: (subcommand_path, positional_args_after_instance, fake_method_name, action_phrase_substring)
# Full invocation will be: [<subcommand_path...>, "prod", *positional_args_after_instance, --body? --state-dir <s> --allow-write?]
_BODY = '{"x":1}'
_BODY_OPT = ["--body", _BODY]

WRITE_CASES = [
    # charts
    ((["charts", "create"], [], _BODY_OPT, "create_chart", "create a chart")),
    ((["charts", "update"], ["7"], _BODY_OPT, "update_chart", "update chart 7")),
    ((["charts", "delete"], ["7"], [], "delete_chart", "delete chart 7")),
    ((["charts", "favorite"], ["7"], [], "favorite_chart", "favorite chart 7")),
    ((["charts", "unfavorite"], ["7"], [], "unfavorite_chart", "unfavorite chart 7")),
    # dashboards
    ((["dashboards", "create"], [], _BODY_OPT, "create_dashboard", "create a dashboard")),
    ((["dashboards", "update"], ["rev"], _BODY_OPT, "update_dashboard", "update dashboard rev")),
    ((["dashboards", "delete"], ["rev"], [], "delete_dashboard", "delete dashboard rev")),
    ((["dashboards", "favorite"], ["rev"], [], "favorite_dashboard", "favorite dashboard rev")),
    ((["dashboards", "unfavorite"], ["rev"], [], "unfavorite_dashboard", "unfavorite dashboard rev")),
    ((["dashboards", "copy"], ["rev"], _BODY_OPT, "copy_dashboard", "copy dashboard rev")),
    # datasets
    ((["datasets", "create"], [], _BODY_OPT, "create_dataset", "create a dataset")),
    ((["datasets", "update"], ["21"], _BODY_OPT, "update_dataset", "update dataset 21")),
    ((["datasets", "delete"], ["21"], [], "delete_dataset", "delete dataset 21")),
    ((["datasets", "refresh"], ["21"], [], "refresh_dataset", "refresh dataset 21")),
    # databases
    ((["databases", "create"], [], _BODY_OPT, "create_database", "create a database")),
    ((["databases", "update"], ["31"], _BODY_OPT, "update_database", "update database 31")),
    ((["databases", "delete"], ["31"], [], "delete_database", "delete database 31")),
    ((["databases", "test-connection"], [], _BODY_OPT, "test_database_connection", "test-connection")),
    # saved queries
    ((["saved-queries", "create"], [], _BODY_OPT, "create_saved_query", "create a saved query")),
    ((["saved-queries", "update"], ["1"], _BODY_OPT, "update_saved_query", "update saved query 1")),
    ((["saved-queries", "delete"], ["1"], [], "delete_saved_query", "delete saved query 1")),
    # sqllab
    ((["sqllab", "execute"], [], _BODY_OPT, "execute_sql", "execute SQL")),
    ((["sqllab", "format-sql"], [], _BODY_OPT, "format_sql", "format SQL")),
    ((["sqllab", "estimate"], [], _BODY_OPT, "estimate_sql", "estimate SQL cost")),
    ((["sqllab", "stop-query"], [], _BODY_OPT, "stop_sql_query", "stop a SQL Lab query")),
    # tags
    ((["tags", "create"], [], _BODY_OPT, "create_tag", "create a tag")),
    ((["tags", "update"], ["1"], _BODY_OPT, "update_tag", "update tag 1")),
    ((["tags", "delete"], ["1"], [], "delete_tag", "delete tag 1")),
    # themes
    ((["themes", "create"], [], _BODY_OPT, "create_theme", "create a theme")),
    ((["themes", "update"], ["1"], _BODY_OPT, "update_theme", "update theme 1")),
    ((["themes", "delete"], ["1"], [], "delete_theme", "delete theme 1")),
    # security
    ((["security", "role-create"], [], _BODY_OPT, "create_role", "create a security role")),
    ((["security", "role-update"], ["5"], _BODY_OPT, "update_role", "update security role 5")),
    ((["security", "role-delete"], ["5"], [], "delete_role", "delete security role 5")),
    ((["security", "user-create"], [], _BODY_OPT, "create_user", "create a security user")),
    ((["security", "user-update"], ["2"], _BODY_OPT, "update_user", "update security user 2")),
    ((["security", "user-delete"], ["2"], [], "delete_user", "delete security user 2")),
    ((["security", "rls", "create"], [], _BODY_OPT, "create_rls_rule", "create a row-level security rule")),
    ((["security", "rls", "update"], ["3"], _BODY_OPT, "update_rls_rule", "update row-level security rule 3")),
    ((["security", "rls", "delete"], ["3"], [], "delete_rls_rule", "delete row-level security rule 3")),
]


def _build_args(
    config_path: Path, state_dir: Path,
    subcommand_path: list[str], positional: list[str], extras: list[str],
    *, allow_write: bool, json_out: bool = False,
) -> list[str]:
    args = ["--config", str(config_path)] + subcommand_path + ["prod"] + positional + extras
    args += ["--state-dir", str(state_dir)]
    if allow_write:
        args.append("--allow-write")
    if json_out:
        args.append("--json")
    return args


@pytest.mark.parametrize("subcommand_path, positional, extras, fake_method, action_phrase", WRITE_CASES)
def test_write_command_refuses_without_allow_write(
    monkeypatch, instance_setup, subcommand_path, positional, extras, fake_method, action_phrase
) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    args = _build_args(config_path, state_dir, subcommand_path, positional, extras, allow_write=False)
    result = runner.invoke(app, args)
    assert result.exit_code == 1, result.stdout
    assert "Re-run with --allow-write" in result.stdout
    assert action_phrase in result.stdout
    assert captured == []


@pytest.mark.parametrize("subcommand_path, positional, extras, fake_method, action_phrase", WRITE_CASES)
def test_write_command_runs_with_allow_write(
    monkeypatch, instance_setup, subcommand_path, positional, extras, fake_method, action_phrase
) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    args = _build_args(config_path, state_dir, subcommand_path, positional, extras, allow_write=True)
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.stdout
    assert len(captured) == 1
    names = [c[0] for c in captured[0].calls]
    assert fake_method in names


@pytest.mark.parametrize("subcommand_path, positional, extras, fake_method, action_phrase", WRITE_CASES)
def test_write_command_json_output(
    monkeypatch, instance_setup, subcommand_path, positional, extras, fake_method, action_phrase
) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    args = _build_args(config_path, state_dir, subcommand_path, positional, extras, allow_write=True, json_out=True)
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["name"] == fake_method


def test_write_command_invalid_body_json_exits_nonzero(monkeypatch, instance_setup) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    args = _build_args(
        config_path, state_dir,
        ["charts", "create"], [], ["--body", "{not-json"],
        allow_write=True,
    )
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "Invalid JSON for --body" in result.stdout
    assert captured == []


def test_write_command_body_from_file(tmp_path: Path, monkeypatch, instance_setup) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    payload_file = tmp_path / "body.json"
    payload_file.write_text(json.dumps({"name": "from-file"}))
    args = _build_args(
        config_path, state_dir,
        ["charts", "create"], [], ["--file", str(payload_file)],
        allow_write=True,
    )
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.stdout
    assert len(captured) == 1
    name, args_tuple, kwargs = captured[0].calls[0]
    assert name == "create_chart"
    assert kwargs == {"body": {"name": "from-file"}}


def test_write_command_body_and_file_conflict(tmp_path: Path, monkeypatch, instance_setup) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    payload_file = tmp_path / "body.json"
    payload_file.write_text("{}")
    args = _build_args(
        config_path, state_dir,
        ["charts", "create"], [], ["--body", "{}", "--file", str(payload_file)],
        allow_write=True,
    )
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "Pass either --body or --file" in result.stdout
    assert captured == []


def test_write_command_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")
    result = runner.invoke(
        app,
        ["--config", str(config_path), "charts", "delete", "ghost", "7", "--state-dir", str(tmp_path / "state"), "--allow-write"],
    )
    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_write_command_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(app, ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"])
    result = runner.invoke(
        app,
        ["--config", str(config_path), "charts", "delete", "prod", "7", "--state-dir", str(tmp_path / "state"), "--allow-write"],
    )
    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_import_unknown_resource_exits_nonzero(tmp_path: Path, monkeypatch, instance_setup) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    bundle = tmp_path / "b.zip"
    bundle.write_bytes(b"PK")
    args = ["--config", str(config_path), "import", "upload", "prod", "ghost", "--file", str(bundle), "--state-dir", str(state_dir), "--allow-write"]
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "Unsupported import resource" in result.stdout
    assert captured == []


def test_import_missing_file_exits_nonzero(tmp_path: Path, monkeypatch, instance_setup) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    args = ["--config", str(config_path), "import", "upload", "prod", "dashboard", "--file", str(tmp_path / "missing.zip"), "--state-dir", str(state_dir), "--allow-write"]
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "Import file not found" in result.stdout
    assert captured == []


def test_import_refuses_without_allow_write(tmp_path: Path, monkeypatch, instance_setup) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    bundle = tmp_path / "b.zip"
    bundle.write_bytes(b"PK")
    args = ["--config", str(config_path), "import", "upload", "prod", "dashboard", "--file", str(bundle), "--state-dir", str(state_dir)]
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "import dashboard bundle 'b.zip'" in result.stdout
    assert "Re-run with --allow-write" in result.stdout
    assert captured == []


def test_import_runs_with_allow_write(tmp_path: Path, monkeypatch, instance_setup) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    bundle = tmp_path / "b.zip"
    bundle.write_bytes(b"PK")
    args = [
        "--config", str(config_path), "import", "upload", "prod", "dashboard",
        "--file", str(bundle), "--passwords", '{"a.zip":"hunter2"}', "--overwrite",
        "--state-dir", str(state_dir), "--allow-write",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.stdout
    assert len(captured) == 1
    name, args_tuple, kwargs = captured[0].calls[0]
    assert name == "import_assets"
    assert args_tuple[0] == "dashboard"
    assert kwargs["passwords"] == {"a.zip": "hunter2"}
    assert kwargs["overwrite"] is True


def test_import_invalid_passwords_json(tmp_path: Path, monkeypatch, instance_setup) -> None:
    config_path, state_dir, captured = _setup(monkeypatch, instance_setup)
    bundle = tmp_path / "b.zip"
    bundle.write_bytes(b"PK")
    args = [
        "--config", str(config_path), "import", "upload", "prod", "dashboard",
        "--file", str(bundle), "--passwords", "not-json",
        "--state-dir", str(state_dir), "--allow-write",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "Invalid JSON for --passwords" in result.stdout
    assert captured == []
