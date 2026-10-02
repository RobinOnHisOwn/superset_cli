import json

import httpx
import pytest
from typer.testing import CliRunner

from superset_cli import cli
from superset_cli.client import AuthExpiredError, SupersetClient

runner = CliRunner()


def invoke(setup, *args):
    config, state = setup
    return runner.invoke(cli.app, ["--config", str(config), "api", "prod", *args, "--state-dir", str(state)])


def mock_http(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(**kw, transport=httpx.MockTransport(handler)))


def test_api_query_and_raw_json(monkeypatch, instance_setup):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"result": {"id": 7}})
    mock_http(monkeypatch, handler)
    result = invoke(instance_setup, "/api/v1/dashboard/", "--param", "q={}", "--param", "x=a=b", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"result": {"id": 7}}
    assert calls[-1].url.params["x"] == "a=b"


@pytest.mark.parametrize("path", ["https://evil.example/api/v1/me/", "//evil.example/api/v1/me/", "/api/v1/../logout", "/api/v1/%2e%2e/logout", "/api/v1/me/#x", "/api/v1/\\evil"])
def test_api_rejects_unsafe_paths(instance_setup, path):
    result = invoke(instance_setup, path)
    assert result.exit_code == 2


def test_write_guard_precedes_auth(monkeypatch, instance_setup):
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("must not import"))
    result = invoke(instance_setup, "/api/v1/chart/", "--method", "POST")
    assert result.exit_code == 1
    assert "--allow-write" in result.output


def test_write_csrf_and_body(monkeypatch, instance_setup):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith("csrf_token/"):
            return httpx.Response(200, json={"result": "csrf"})
        return httpx.Response(200, json={"result": {"id": 7}})
    mock_http(monkeypatch, handler)
    result = invoke(instance_setup, "/api/v1/chart/", "--method", "POST", "--body", '{"slice_name":"Test"}', "--allow-write")
    assert result.exit_code == 0, result.output
    assert calls[-1].headers["X-CSRFToken"] == "csrf"
    assert json.loads(calls[-1].content) == {"slice_name": "Test"}
    assert '"id": 7' in result.output


@pytest.mark.parametrize("missing", [False, True])
def test_auto_auth_once(monkeypatch, instance_setup, missing):
    config, state = instance_setup
    path = cli.get_storage_state_path(state_dir=state, instance_name="prod")
    if missing:
        path.unlink()
    refreshed = []
    def handler(request):
        if not refreshed:
            return httpx.Response(401, json={"message": "expired"})
        return httpx.Response(200, json={"result": {"id": 1}})
    mock_http(monkeypatch, handler)
    def importer(**kw):
        refreshed.append(True)
        path.write_text('{"cookies":[],"origins":[]}')
        assert kw["validate"](path)
        return {}
    monkeypatch.setattr(cli, "import_browser_cookies", importer)
    result = invoke(instance_setup, "/api/v1/me/", "--json")
    assert result.exit_code == 0, result.output
    assert len(refreshed) == 1
    assert json.loads(result.stdout)["result"]["id"] == 1


def test_network_error_does_not_import(monkeypatch, instance_setup):
    def handler(request):
        raise httpx.ConnectError("offline", request=request)
    mock_http(monkeypatch, handler)
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("must not import"))
    result = invoke(instance_setup, "/api/v1/me/")
    assert result.exit_code == 1
    assert "Network error" in result.output


def test_custom_request_does_not_follow_redirects(monkeypatch, instance_setup):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"location": "https://evil.example/"})
    mock_http(monkeypatch, handler)
    path = cli.get_storage_state_path(state_dir=instance_setup[1], instance_name="prod")
    with SupersetClient(base_url="https://superset.example.com", storage_state_path=path) as client:
        with pytest.raises(AuthExpiredError):
            client.request("GET", "/api/v1/me/")
    assert len(calls) == 1


def test_recovery_failure_is_bounded(monkeypatch, instance_setup):
    imports = []
    mock_http(monkeypatch, lambda request: httpx.Response(401, json={}))
    def importer(**kw):
        imports.append(True)
        assert not kw["validate"](kw["storage_state_path"])
        raise cli.NoCookiesFoundError("Sign in in your browser first.")
    monkeypatch.setattr(cli, "import_browser_cookies", importer)
    result = invoke(instance_setup, "/api/v1/me/")
    assert result.exit_code == 1
    assert len(imports) == 1
    assert "Sign in" in result.output


def test_sent_write_is_not_retried(monkeypatch, instance_setup):
    writes = []
    def handler(request):
        if request.method == "POST":
            writes.append(request)
            return httpx.Response(401, json={})
        return httpx.Response(200, json={"result": "token"})
    mock_http(monkeypatch, handler)
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("no recovery after mutation"))
    result = invoke(instance_setup, "/api/v1/chart/", "--method", "POST", "--allow-write")
    assert result.exit_code == 1
    assert len(writes) == 1


@pytest.mark.parametrize("args", [["--param", "bad"], ["--method", "TRACE"], ["--body", "{}"], ["--method", "POST", "--allow-write", "--body", "[]"]])
def test_invalid_options(instance_setup, args):
    assert invoke(instance_setup, "/api/v1/chart/", *args).exit_code == 2


def test_null_body_rejected_before_network(monkeypatch, instance_setup):
    mock_http(monkeypatch, lambda request: pytest.fail("invalid body must not reach network"))
    result = invoke(instance_setup, "/api/v1/chart/", "--method", "POST", "--allow-write", "--body", "null")
    assert result.exit_code == 2, result.exception
    assert "JSON object" in result.output


def test_permission_failure_does_not_import(monkeypatch, instance_setup):
    mock_http(monkeypatch, lambda request: httpx.Response(403, json={}))
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("not an auth failure"))
    result = invoke(instance_setup, "/api/v1/me/")
    assert result.exit_code == 1
    assert "HTTP 403" in result.output
