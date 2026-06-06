# conftest.py — pytest hooks and shared fixtures only.
# Test helpers live in tests/fakes.py.

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from superset_cli.cli import app

_runner = CliRunner()

_SESSION_COOKIE = {
    "name": "session",
    "value": "abc",
    "domain": "superset.example.com",
    "path": "/",
    "expires": -1,
    "httpOnly": True,
    "secure": True,
    "sameSite": "Lax",
}


@pytest.fixture
def instance_setup(tmp_path: Path) -> tuple[Path, Path]:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    storage_state_path = state_dir / "prod" / "storage-state.json"
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    storage_state_path.write_text('{"cookies":[],"origins":[]}')
    result = _runner.invoke(app, ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"])
    assert result.exit_code == 0
    return config_path, state_dir


@pytest.fixture
def instance_setup_with_session(tmp_path: Path) -> tuple[Path, Path, Path]:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    storage_state_path = state_dir / "prod" / "storage-state.json"
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    storage_state_path.write_text(json.dumps({"cookies": [_SESSION_COOKIE], "origins": []}))
    result = _runner.invoke(app, ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"])
    assert result.exit_code == 0
    return config_path, state_dir, storage_state_path
