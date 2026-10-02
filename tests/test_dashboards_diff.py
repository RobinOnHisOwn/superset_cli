import json
from pathlib import Path

from typer.testing import CliRunner

from superset_cli.cli import app, diff_dashboard_records

runner = CliRunner()


def _add_prod_instance(config_path: Path) -> None:
    config_path.write_text(
        "instances:\n  - name: prod\n    base_url: https://superset.example.com\n"
    )


def _save_state(state_dir: Path) -> None:
    d = state_dir / "prod"
    d.mkdir(parents=True, exist_ok=True)
    (d / "storage-state.json").write_text(json.dumps({"cookies": [], "origins": []}))


def test_diff_dashboard_records_reports_only_differing_fields():
    a = {"id": 1, "css": None, "published": True, "uuid": "x"}
    b = {"id": 2, "css": ".x{}", "published": True, "uuid": "y"}
    diffs = diff_dashboard_records(a, b)
    fields = {d[0] for d in diffs}
    assert "css" in fields
    assert "published" not in fields  # equal
    assert "id" not in fields and "uuid" not in fields  # skipped identity fields


def test_diff_dashboard_records_truncates_large_values():
    a = {"position_json": "A" * 5000}
    b = {"position_json": "B" * 5000}
    diffs = diff_dashboard_records(a, b)
    field, va, vb = diffs[0]
    assert field == "position_json"
    assert len(va) <= 400 and len(vb) <= 400


def test_dashboards_diff_command_runs(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)
    _save_state(state_dir)

    records = {
        "7": {"id": 7, "dashboard_title": "A", "css": None},
        "8": {"id": 8, "dashboard_title": "B", "css": ".x{}"},
    }

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_dashboard(self, i):
            return records[i]

    monkeypatch.setattr("superset_cli.cli.SupersetClient", Client)
    result = runner.invoke(
        app,
        ["--config", str(config_path), "dashboards", "diff", "prod", "7", "8", "--state-dir", str(state_dir)],
    )
    assert result.exit_code == 0
    assert "css" in result.stdout
