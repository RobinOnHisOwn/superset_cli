import json

import httpx
import pytest
from typer.testing import CliRunner

from superset_cli import cli
from superset_cli.config import load_config

runner = CliRunner()
HTTP_CLIENT = httpx.Client
KEY = "sst_synthetic-test-key"


def invoke(setup, *command):
    config, state = setup
    return runner.invoke(cli.app, ["--config", str(config), *command, "--state-dir", str(state)])


def setup_transport(monkeypatch, handler):
    monkeypatch.setattr(httpx, "Client", lambda **kw: HTTP_CLIENT(**kw, transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("API keys must not import browser cookies"))


def bind(setup):
    return invoke(setup, "auth", "api-key", "set", "prod", "--env", "EXAMPLE_SUPERSET_API_KEY", "--json")


def test_api_key_binding_reads_writes_status_and_clear(monkeypatch, instance_setup):
    config, state = instance_setup
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", KEY)
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == f"Bearer {KEY}"
        assert "Cookie" not in request.headers
        if request.url.path.endswith("csrf_token/"):
            return httpx.Response(200, json={"result": "csrf"})
        if request.method == "PUT":
            assert request.headers["X-CSRFToken"] == "csrf"
        return httpx.Response(200, json={"count": 1, "result": [{"id": 1, "slice_name": "Example"}]})
    setup_transport(monkeypatch, handler)
    result = bind(instance_setup)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"mode": "api_key", "env": "EXAMPLE_SUPERSET_API_KEY", "prefix": "sst_"}
    assert KEY not in config.read_text()
    for command in [("charts", "list", "prod", "--json"),
                    ("api", "prod", "/api/v1/chart/1", "--method", "PUT", "--body", "{}", "--allow-write", "--json"),
                    ("charts", "update", "prod", "1", "--body", "{}", "--allow-write", "--json")]:
        result = invoke(instance_setup, *command)
        assert result.exit_code == 0, result.output
        assert KEY not in result.output
    assert not (state / "prod" / "api-key-state.json").exists()
    (state / "prod" / "storage-state.json").unlink()
    result = invoke(instance_setup, "auth", "status", "prod", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["credential_available"] is True
    assert json.loads(result.stdout)["mode"] == "api_key"
    result = invoke(instance_setup, "auth", "api-key", "clear", "prod", "--json")
    assert result.exit_code == 0, result.output
    assert load_config(config).instances[0].auth is None


@pytest.mark.parametrize("key", [None, "", "jwt-like-token", "sst_bad\nheader", "sst_"])
def test_api_key_invalid_secret_fails_before_network(monkeypatch, instance_setup, key):
    if key is None:
        monkeypatch.delenv("EXAMPLE_SUPERSET_API_KEY", raising=False)
    else:
        monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", key)
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("invalid credentials must not access network"))
    before = instance_setup[0].read_text()
    result = bind(instance_setup)
    assert result.exit_code == 1, result.output
    assert instance_setup[0].read_text() == before
    if key:
        assert key not in result.output


@pytest.mark.parametrize("status", [401, 403, 302])
def test_api_key_rejected_binding_does_not_persist_or_follow_redirects(monkeypatch, instance_setup, status):
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", KEY)
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"location": "https://other.example.com/"}, json={"message": "denied"})
    setup_transport(monkeypatch, handler)
    before = instance_setup[0].read_text()
    result = bind(instance_setup)
    assert result.exit_code == 1, result.output
    assert len(calls) == 1
    assert instance_setup[0].read_text() == before
    assert KEY not in result.output


def test_api_key_expired_environment_and_write_guard(monkeypatch, instance_setup):
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", KEY)
    setup_transport(monkeypatch, lambda request: httpx.Response(200, json={"result": {}}))
    assert bind(instance_setup).exit_code == 0
    monkeypatch.delenv("EXAMPLE_SUPERSET_API_KEY")
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("must not access network"))
    result = invoke(instance_setup, "api", "prod", "/api/v1/chart/1", "--method", "PUT")
    assert result.exit_code == 1
    assert "--allow-write" in result.output
    result = invoke(instance_setup, "charts", "list", "prod", "--json")
    assert result.exit_code == 1
    assert "environment" in result.stderr.lower()


def test_api_key_auth_does_not_recover_or_replay_mutation(monkeypatch, instance_setup):
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", KEY)
    setup_transport(monkeypatch, lambda request: httpx.Response(200, json={"result": {}}))
    assert bind(instance_setup).exit_code == 0
    writes = []
    def handler(request):
        if request.method == "PUT":
            writes.append(request)
            return httpx.Response(401, json={})
        return httpx.Response(200, json={"result": "csrf"})
    setup_transport(monkeypatch, handler)
    result = invoke(instance_setup, "api", "prod", "/api/v1/chart/1", "--method", "PUT", "--allow-write")
    assert result.exit_code == 1
    assert len(writes) == 1
    assert "API key" in result.output
    assert KEY not in result.output


def test_api_key_rotates_environment_and_preserves_browser_state(monkeypatch, instance_setup):
    state_path = instance_setup[1] / "prod" / "storage-state.json"
    before = state_path.read_bytes()
    headers = []
    def handler(request):
        headers.append(request.headers["Authorization"])
        return httpx.Response(200, json={"count": 0, "result": []})
    setup_transport(monkeypatch, handler)
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", KEY)
    assert bind(instance_setup).exit_code == 0
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", "sst_rotated-synthetic-key")
    assert invoke(instance_setup, "charts", "list", "prod", "--json").exit_code == 0
    assert headers[-1] == "Bearer sst_rotated-synthetic-key"
    assert state_path.read_bytes() == before
    result = invoke(instance_setup, "auth", "login", "prod")
    assert result.exit_code == 1
    assert "does not import browser" in result.stderr
    result = invoke(instance_setup, "auth", "logout", "prod")
    assert result.exit_code == 1
    assert "auth api-key clear" in result.stderr
    assert state_path.read_bytes() == before


def test_api_key_custom_prefix_and_tls_boundary(monkeypatch, instance_setup):
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", "custom_synthetic-key")
    setup_transport(monkeypatch, lambda request: httpx.Response(200, json={"result": {}}))
    result = invoke(instance_setup, "auth", "api-key", "set", "prod", "--env", "EXAMPLE_SUPERSET_API_KEY", "--prefix", "custom_")
    assert result.exit_code == 0, result.output
    config = load_config(instance_setup[0])
    config.instances[0].base_url = "http://superset.example.com"
    from superset_cli.config import save_config
    save_config(config, instance_setup[0])
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("insecure request"))
    result = invoke(instance_setup, "charts", "list", "prod", "--json")
    assert result.exit_code == 1
    assert "HTTPS" in result.stderr


def test_api_key_clear_preserves_other_selected_mode(instance_setup):
    from superset_cli.config import save_config
    from superset_cli.models import AuthConfig
    config = load_config(instance_setup[0])
    config.instances[0].auth = AuthConfig(mode="jwt")
    save_config(config, instance_setup[0])
    result = invoke(instance_setup, "auth", "api-key", "clear", "prod", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["mode"] == "jwt"
    assert load_config(instance_setup[0]).instances[0].auth.mode == "jwt"


def test_api_key_non_json_response_does_not_advise_browser_login(monkeypatch, instance_setup):
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", KEY)
    setup_transport(monkeypatch, lambda request: httpx.Response(200, text="<html>Sign in</html>"))
    before = instance_setup[0].read_text()
    result = bind(instance_setup)
    assert result.exit_code == 1
    assert "API key" in result.output
    assert "auth login" not in result.output
    assert instance_setup[0].read_text() == before
