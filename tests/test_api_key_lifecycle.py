import json

import httpx
import pytest
from rich.text import Text
from typer.testing import CliRunner

from superset_cli import cli

runner = CliRunner()
HTTP_CLIENT = httpx.Client
UUID = "12345678-1234-4234-8234-123456789abc"
SECRET = "sst_do-not-display"
BASE = "/api/v1/security/api_keys/"


def invoke(setup, *args):
    config, state, _ = setup
    return runner.invoke(cli.app, ["--config", str(config), "auth", "api-key", *args,
                                   "--state-dir", str(state)])


def transport(monkeypatch, handler):
    monkeypatch.setattr(httpx, "Client", lambda **kw: HTTP_CLIENT(**kw, transport=httpx.MockTransport(handler)))


@pytest.mark.parametrize("command", ["list", "get"])
@pytest.mark.parametrize("as_json", [False, True])
def test_metadata_only(monkeypatch, instance_setup_with_session, command, as_json):
    calls = []
    metadata = {"uuid": UUID, "name": "Example key", "active": True,
                "key": SECRET, "key_hash": SECRET, "unexpected": {"key": SECRET}}

    def handler(request):
        calls.append((request.method, request.url.path, str(request.url.query)))
        return httpx.Response(200, json={"result": [metadata] if command == "list" else metadata,
                                         "key": SECRET})

    transport(monkeypatch, handler)
    args = [command, "prod", *([UUID] if command == "get" else []), *(["--json"] if as_json else [])]
    result = invoke(instance_setup_with_session, *args)
    assert result.exit_code == 0, result.output
    assert SECRET not in result.output
    assert "Example key" in result.stdout
    assert len(calls) == 1
    assert calls[0][:2] == ("GET", BASE + (UUID if command == "get" else ""))
    if as_json:
        clean = {"uuid": UUID, "name": "Example key", "active": True}
        assert json.loads(result.stdout) == {"result": [clean] if command == "list" else clean}


@pytest.mark.parametrize("args", [["revoke", "prod", UUID], ["get", "prod", "../bad"],
                                   ["revoke", "prod", "bad", "--allow-write"]])
def test_rejects_before_credentials(monkeypatch, instance_setup_with_session, args):
    monkeypatch.setattr(cli, "_require_storage_state", lambda **kw: pytest.fail("credential access"))
    monkeypatch.setattr(cli, "_client", lambda **kw: pytest.fail("client access"))
    result = invoke(instance_setup_with_session, *args)
    assert result.exit_code != 0
    assert "--allow-write" in result.output if len(args) == 3 and args[0] == "revoke" else "UUID" in result.output


@pytest.mark.parametrize("outcome", ["verified", "still-active", "self-revoked", "timeout", "delete-error", "wrong-uuid", "missing-time"])
@pytest.mark.parametrize("as_json", [False, True])
def test_revoke_requires_readback_never_replays(monkeypatch, instance_setup_with_session, outcome, as_json):
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("csrf_token/"):
            return httpx.Response(200, json={"result": "csrf"})
        if request.method == "DELETE":
            assert request.headers["X-CSRFToken"] == "csrf"
            if outcome == "timeout":
                raise httpx.ReadTimeout(SECRET, request=request)
            if outcome == "delete-error":
                return httpx.Response(500, json={"message": SECRET})
            return httpx.Response(200, json={"message": SECRET})
        after_delete = any(method == "DELETE" for method, _ in calls)
        if after_delete and outcome == "self-revoked":
            return httpx.Response(401, json={"message": SECRET})
        return httpx.Response(200, json={"result": {
            "uuid": UUID if not after_delete or outcome != "wrong-uuid" else "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "active": not after_delete or outcome == "still-active",
            "revoked_on": "2026-10-07T12:00:00" if after_delete and outcome != "missing-time" else None,
            "key": SECRET,
        }})

    transport(monkeypatch, handler)
    result = invoke(instance_setup_with_session, "revoke", "prod", UUID, "--allow-write", *(["--json"] if as_json else []))
    assert (result.exit_code == 0) == (outcome == "verified"), result.output
    assert SECRET not in result.output
    assert calls.count(("DELETE", BASE + UUID)) == 1
    if outcome == "verified":
        assert calls[-1] == ("GET", BASE + UUID)
        if as_json:
            assert json.loads(result.stdout)["result"]["active"] is False
        else:
            assert "revocation verified" in result.stdout.lower()
    else:
        assert "unverified" in result.output.lower()
        assert UUID in result.output


@pytest.mark.parametrize("status", [401, 403, 404, 500])
@pytest.mark.parametrize("command", ["list", "get", "revoke"])
def test_http_failure_does_not_leak_or_delete(monkeypatch, instance_setup_with_session, status, command):
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(status, json={"message": SECRET})

    transport(monkeypatch, handler)
    result = invoke(instance_setup_with_session, command, "prod", *([UUID] if command != "list" else []),
                    *(["--allow-write"] if command == "revoke" else []))
    assert result.exit_code != 0
    assert SECRET not in result.output
    assert calls == ["GET"]


@pytest.mark.parametrize("env", [{"FORCE_COLOR": "1", "TERM": "xterm-256color"}, {"NO_COLOR": "1", "TERM": "dumb"}])
def test_lifecycle_help(env):
    result = runner.invoke(cli.app, ["auth", "api-key", "revoke", "--help"], env=env)
    assert result.exit_code == 0
    plain = " ".join(Text.from_ansi(result.stdout).plain.replace("│", " ").split())
    assert "Required to actually perform the write. Without it the command is a dry-run." in plain
