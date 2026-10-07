import json

import httpx
import pytest
from typer.testing import CliRunner

from superset_cli import cli

runner = CliRunner()


def invoke(setup, timeout=None, command=None):
    config, state = setup
    args = ["--config", str(config)]
    if timeout is not None:
        args += ["--timeout", timeout]
    args += command or ["api", "prod", "/api/v1/chart/"]
    return runner.invoke(cli.app, [*args, "--state-dir", str(state)])


@pytest.mark.parametrize("command", [
    ["api", "prod", "/api/v1/chart/", "--method", "POST", "--allow-write"],
    ["charts", "data", "prod", "7", "--json"],
    ["sqllab", "execute", "prod", "--body", '{"database_id":1,"sql":"SELECT 1"}', "--allow-write"],
])
def test_timeout_covers_requests_and_resets(monkeypatch, instance_setup, command):
    original = httpx.Client
    calls = []

    def handler(request):
        calls.append((request.url.path, request.extensions["timeout"]))
        if request.url.path.endswith("csrf_token/"):
            return httpx.Response(200, json={"result": "csrf"})
        if request.url.path.endswith("/chart/7"):
            return httpx.Response(200, json={"result": {"query_context": json.dumps({"queries": [{}]})}})
        return httpx.Response(200, json={"result": [{"status": "success", "data": [{"value": 1}]}]})

    monkeypatch.setattr(httpx, "Client", lambda **kw: original(**kw, transport=httpx.MockTransport(handler)))
    for option, seconds in [("90.5", 90.5), (None, 30.0)]:
        calls.clear()
        result = invoke(instance_setup, option, command)
        assert result.exit_code == 0, result.output
        assert calls
        assert all(set(values.values()) == {seconds} for _, values in calls)


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "nope"])
def test_timeout_invalid_before_io(monkeypatch, instance_setup, value):
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("must not access network"))
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("must not access browser"))
    result = invoke(instance_setup, value)
    assert result.exit_code == 2
    assert "finite positive" in result.output or "valid float" in result.output


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_timeout_diagnostic_never_retries_mutation(monkeypatch, instance_setup, method):
    original = httpx.Client
    calls = []

    def handler(request):
        if request.url.path.endswith("/chart/"):
            calls.append(request.method)
            raise httpx.ReadTimeout("secret diagnostic", request=request)
        return httpx.Response(200, json={"result": "csrf"})

    monkeypatch.setattr(httpx, "Client", lambda **kw: original(**kw, transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("must not access browser"))
    result = invoke(instance_setup, "90", ["api", "prod", "/api/v1/chart/", "--method", method, "--allow-write"])
    assert result.exit_code == 1
    assert "timed out" in result.stderr
    assert ("outcome unknown" in result.stderr) == (method == "POST")
    assert "secret diagnostic" not in result.output
    assert calls == [method]


def test_timeout_preserves_write_guard(monkeypatch, instance_setup):
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("must not access network"))
    result = invoke(instance_setup, "90", ["api", "prod", "/api/v1/chart/", "--method", "POST"])
    assert result.exit_code == 1
    assert "--allow-write" in result.output


def test_timeout_covers_jwt_login_refresh_and_recovery(monkeypatch, instance_setup):
    original = httpx.Client
    calls = []
    monkeypatch.setenv("EXAMPLE_USER", "reader")
    monkeypatch.setenv("EXAMPLE_PASSWORD", "synthetic-password")

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"access_token": "old", "refresh_token": "refresh"})
        if request.url.path.endswith("/refresh"):
            return httpx.Response(200, json={"access_token": "new"})
        if request.headers["Authorization"] == "Bearer old":
            return httpx.Response(401, json={})
        return httpx.Response(200, json={"result": []})

    monkeypatch.setattr(httpx, "Client", lambda **kw: original(**kw, transport=httpx.MockTransport(handler)))
    login = ["auth", "jwt", "login", "prod", "--username-env", "EXAMPLE_USER", "--password-env", "EXAMPLE_PASSWORD"]
    for command in [login, ["api", "prod", "/api/v1/chart/"], ["auth", "jwt", "refresh", "prod"]]:
        result = invoke(instance_setup, "75", command)
        assert result.exit_code == 0, result.output
    assert [r.url.path for r in calls].count("/api/v1/security/refresh") == 2
    assert all(set(r.extensions["timeout"].values()) == {75.0} for r in calls)
