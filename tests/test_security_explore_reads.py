import json

import httpx
import pytest
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import SupersetClient


CASES = [
    (["security", "roles", "list", "prod"], "/api/v1/security/roles/", True, "Analyst"),
    (["security", "roles", "get", "prod", "7"], "/api/v1/security/roles/7", False, "Analyst"),
    (["security", "users", "list", "prod"], "/api/v1/security/users/", True, "reader"),
    (["security", "users", "get", "prod", "7"], "/api/v1/security/users/7", False, "reader"),
    (["security", "rls", "list", "prod"], "/api/v1/rowlevelsecurity/", True, "Analyst"),
    (["security", "rls", "get", "prod", "7"], "/api/v1/rowlevelsecurity/7", False, "Analyst"),
    (["explore", "show", "prod", "--slice-id", "7"], "/api/v1/explore/", False, "Analyst"),
    (["explore", "form-data", "prod", "key"], "/api/v1/explore/form_data/key", False, "Analyst"),
]


@pytest.mark.parametrize("args,path,is_list,label", CASES)
@pytest.mark.parametrize("mode", ["json", "human", "empty", "not-found"])
def test_security_explore_reads(monkeypatch, instance_setup, args, path, is_list, label, mode):
    config, state = instance_setup
    item = {"id": 7, "name": "Analyst", "username": "reader"}
    payload = {"count": 1, "result": [item]} if is_list else {"result": item}
    if mode == "empty":
        payload = {"count": 0, "result": []} if is_list else {"result": {}}
    if args[:2] == ["explore", "form-data"]:
        payload = {"form_data": {} if mode == "empty" else item}
    seen = []

    def handle(request):
        seen.append(request)
        assert request.method == "GET"
        assert request.url.path == path
        if args[:2] == ["explore", "show"]:
            assert request.url.params["slice_id"] == "7"
        return httpx.Response(404 if mode == "not-found" else 200, json=payload)

    def factory(**kwargs):
        client = SupersetClient(**kwargs)
        client.http.close()
        client.http = httpx.Client(base_url=kwargs["base_url"], transport=httpx.MockTransport(handle))
        return client

    monkeypatch.setattr("superset_cli.cli.SupersetClient", factory)
    result = CliRunner().invoke(app, ["--config", str(config), *args, "--state-dir", str(state),
                                     *(["--json"] if mode == "json" else [])])
    assert result.exit_code == (1 if mode == "not-found" else 0)
    assert len(seen) == 1
    if mode == "json":
        assert json.loads(result.stdout) == (payload if is_list else item)
    elif mode == "human":
        assert label in result.stdout
    elif mode == "empty" and is_list:
        assert "No " in result.stdout
    elif mode == "not-found":
        assert "not found" in result.output.lower()


def test_explore_show_requires_slice_id(instance_setup):
    config, state = instance_setup
    result = CliRunner().invoke(app, ["--config", str(config), "explore", "show", "prod", "--state-dir", str(state)])
    assert result.exit_code == 2
    assert "--slice-id" in result.output
