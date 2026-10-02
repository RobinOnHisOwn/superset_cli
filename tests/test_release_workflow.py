import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_metadata_links_to_canonical_upstream():
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]
    assert project["urls"] == {
        "Source": "https://github.com/RobinOnHisOwn/superset_cli",
        "Issues": "https://github.com/RobinOnHisOwn/superset_cli/issues",
    }


def test_package_declares_mit_license_and_copyright_holder():
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    license_text = (REPO_ROOT / "LICENSE").read_text()
    assert "Copyright (c) 2026 Robin Rittsteiger" in license_text
    assert "Permission is hereby granted, free of charge" in license_text
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in license_text


def release_workflow():
    return yaml.safe_load((REPO_ROOT / ".github/workflows/publish.yml").read_text())


def test_release_workflow_is_gated_and_uses_hosted_runners():
    workflow = release_workflow()
    assert workflow["on"] == {"release": {"types": ["published"]}, "workflow_dispatch": None}
    assert workflow["permissions"] == {"contents": "read"}
    build = workflow["jobs"]["build"]
    publish = workflow["jobs"]["publish"]
    assert build["runs-on"] == publish["runs-on"] == "ubuntu-latest"
    assert publish["needs"] == "build"
    assert publish["if"] == "github.event_name == 'release'"
    assert publish["environment"]["name"] == "pypi"
    assert publish["permissions"] == {"id-token": "write"}
    commands = "\n".join(step.get("run", "") for step in build["steps"])
    for command in ["uv sync --locked --group dev", "uv run pytest -v", "uv build",
                    "--with dist/*.whl", "--with dist/*.tar.gz"]:
        assert command in commands
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
    assert all("run" not in step for step in publish["steps"])
    upload = next(s for s in build["steps"] if s.get("uses", "").startswith("actions/upload-artifact@"))
    download = next(s for s in publish["steps"] if s.get("uses", "").startswith("actions/download-artifact@"))
    assert upload["with"]["name"] == download["with"]["name"]
    assert upload["with"]["path"] == download["with"]["path"] == "dist/"


@pytest.mark.parametrize("tag,success", [("v0.1.0", True), ("v0.2.0", False), ("0.1.0", False)])
def test_release_tag_matches_package_version(tmp_path, tag, success):
    step = next(s for s in release_workflow()["jobs"]["build"]["steps"]
                if s.get("name") == "Check release version")
    # Run the exact workflow command against a tiny package fixture.
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    result = subprocess.run(["bash", "-e", "-c", step["run"]], cwd=tmp_path,
                            env={**os.environ, "RELEASE_TAG": tag, "PATH": f"{Path(sys.executable).parent}:{os.environ['PATH']}"},
                            capture_output=True, text=True)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    if not success:
        assert "does not match package version" in result.stderr
