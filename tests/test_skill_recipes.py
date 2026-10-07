"""Representative companion-skill workflow, entirely against mocked HTTP."""
import json

import httpx
from typer.testing import CliRunner

from superset_cli import cli


def test_skill_recipe_workflow_uses_shared_auth_and_guards(monkeypatch, instance_setup):
    original = httpx.Client
    calls = []
    chart = {"id": 42, "slice_name": "Example", "params": "{}", "query_context": "old"}

    def handler(request):
        calls.append(request)
        path = request.url.path
        if path.endswith("csrf_token/"):
            return httpx.Response(200, json={"result": "synthetic-csrf"})
        if request.method == "PUT":
            assert request.headers["X-CSRFToken"] == "synthetic-csrf"
            chart.update(json.loads(request.content))
            return httpx.Response(200, json={"result": chart})
        if path.endswith("/chart/42/data/"):
            return httpx.Response(200, json={"result": [{"status": "success", "data": [{"value": 1}]}]})
        if path.endswith("/chart/42"):
            return httpx.Response(200, json={"result": chart})
        if "/dashboard/" in path:
            return httpx.Response(200, json={"result": {"id": int(path.rsplit("/", 1)[-1]), "css": ""}})
        return httpx.Response(200, json={"result": {"id": 1, "username": "reader"}})

    monkeypatch.setattr(httpx, "Client", lambda **kw: original(**kw, transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: (_ for _ in ()).throw(AssertionError("no cookie extraction")))
    config, state = instance_setup
    runner = CliRunner()
    base = ["--config", str(config)]
    commands = [
        ["instances", "list", "--json"],
        ["auth", "validate", "prod", "--json"],
        ["charts", "update", "prod", "42", "--clear-query-context", "--allow-write", "--json"],
        ["charts", "get", "prod", "42", "--json"],
        ["charts", "data", "prod", "42", "--json"],
        ["dashboards", "diff", "prod", "7", "8", "--json"],
        ["api", "prod", "/api/v1/me/", "--json"],
    ]
    for command in commands:
        args = command if command[:2] == ["instances", "list"] else [*command, "--state-dir", str(state)]
        result = runner.invoke(cli.app, [*base, *args])
        assert result.exit_code == 0, result.output
        json.loads(result.stdout)
    assert chart["query_context"] is None
    assert len([request for request in calls if request.method == "PUT"]) == 1
    calls.clear()
    result = runner.invoke(cli.app, [*base, "charts", "update", "prod", "42", "--clear-query-context", "--state-dir", str(state)])
    assert result.exit_code == 1
    assert "--allow-write" in result.stdout
    assert calls == []
