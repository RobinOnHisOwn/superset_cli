import io
import json
import subprocess
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from rich.text import Text
from typer.testing import CliRunner

from superset_cli import cli

runner = CliRunner()
HTTP_CLIENT = httpx.Client
OPERATION = "87654321-4321-4321-8321-cba987654321"
KEY_UUID = "12345678-1234-4234-8234-123456789abc"
SECRET = "sst_distinctive-pipeline-secret"
BASE = "/api/v1/security/api_keys/"


@pytest.fixture
def issuance(monkeypatch, instance_setup_with_session):
    class Scenario:
        failure = None
        requests = []
        key = None
        writes = 0
        deletes = 0

        def invoke(self, *extra, allow=True, secret=True):
            config, state, _ = instance_setup_with_session
            return runner.invoke(cli.app, ["--config", str(config), "auth", "api-key", "create", "prod",
                "--name", "Example integration", "--expires-on",
                (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "--operation-id", OPERATION, "--server-timezone", "UTC", "--state-dir", str(state),
                *(["--allow-write"] if allow else []), *(["--secret-output"] if secret else []), *extra])

        def http(self, request):
            self.requests.append(request)
            if request.url.path == "/api/v1/me/roles/":
                grants = [["can_" + perm, "ApiKey"] for perm in ("list", "create", "get", "revoke")]
                if self.failure == "permissions":
                    grants.pop()
                owner = 8 if self.writes and self.failure == "identity" else 7
                return httpx.Response(200, json={"result": {"userId": owner, "isActive": True,
                    "roles": {"Provisioner": grants + [["can_read", "SecurityRestApi"]]}}})
            if request.url.path.endswith("csrf_token/"):
                return httpx.Response(200, json={"result": "csrf"})
            if request.method == "POST":
                self.writes += 1
                body = json.loads(request.content)
                assert request.headers["X-CSRFToken"] == "csrf"
                assert OPERATION in body["name"] and "user" not in body and "scopes" not in body
                assert datetime.fromisoformat(body["expires_on"]).tzinfo is None
                if self.failure == "redirect":
                    return httpx.Response(307, headers={"Location": BASE})
                self.key = {"uuid": KEY_UUID, "name": body["name"], "active": True,
                            "expires_on": body["expires_on"], "revoked_on": None}
                if self.failure == "timeout":
                    raise httpx.ReadTimeout(SECRET, request=request)
                if self.failure == "http-error":
                    return httpx.Response(500, json={"message": SECRET})
                if self.failure == "expiry":
                    self.key["expires_on"] = "2000-01-01T00:00:00"
                issued = {**self.key, "key": SECRET + ("\n" if self.failure == "bad-secret" else "")}
                if self.failure == "bad-uuid":
                    issued["uuid"] = "invalid"
                return httpx.Response(201, json={"result": issued})
            if request.method == "DELETE":
                self.deletes += 1
                if self.failure == "rollback-redirect":
                    return httpx.Response(307, headers={"Location": BASE + KEY_UUID})
                self.key.update(active=False, revoked_on=datetime.now(timezone.utc).isoformat())
                return httpx.Response(200, json={"message": SECRET})
            if request.url.path == BASE:
                keys = [self.key] if self.key else []
                if self.failure == "existing":
                    keys = [{"uuid": KEY_UUID, "name": f"Example [{OPERATION}]"}]
                return httpx.Response(200, json={"result": keys})
            if request.url.path == BASE + KEY_UUID:
                if self.failure == "ownership":
                    return httpx.Response(404, json={"message": SECRET})
                return httpx.Response(200, json={"result": self.key})
            pytest.fail(f"Unexpected request {request.method} {request.url.path}")

    scenario = Scenario()
    scenario.setup = instance_setup_with_session
    monkeypatch.setattr(httpx, "Client", lambda **kw: HTTP_CLIENT(**kw, transport=httpx.MockTransport(scenario.http)))
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("No secret-sink subprocesses"))
    return scenario


@pytest.mark.parametrize("allow,secret", [(False, True), (True, False), (False, False)])
@pytest.mark.parametrize("as_json", [False, True])
def test_both_opt_ins_before_credentials(monkeypatch, issuance, allow, secret, as_json):
    monkeypatch.setattr(cli, "_require_instance", lambda *a, **kw: pytest.fail("config access"))
    result = issuance.invoke(*(["--json"] if as_json else []), allow=allow, secret=secret)
    assert result.exit_code != 0
    assert ("--allow-write" if not allow else "--secret-output") in result.output
    assert SECRET not in result.output and not issuance.requests
    assert result.stdout == ""


def test_json_never_grants_or_mixes_secret_output(issuance):
    result = issuance.invoke("--json")
    assert result.exit_code == 2 and "cannot" in result.output.lower()
    assert SECRET not in result.output and not issuance.requests


def test_secret_only_stdout_no_local_auth_changes(monkeypatch, issuance):
    config, _, state = issuance.setup
    before = (config.read_bytes(), state.read_bytes())
    original = io.open
    def no_writes(file, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax"), "No local secret files"
        return original(file, mode, *args, **kwargs)
    monkeypatch.setattr(io, "open", no_writes)
    result = issuance.invoke()
    assert result.exit_code == 0, result.output
    assert result.stdout == SECRET + "\n" and SECRET not in result.stderr
    metadata = json.loads(result.stderr)
    assert metadata["emitted"] is True and metadata["owner_id"] == 7
    assert metadata["key_uuid"] == KEY_UUID and "stored" not in metadata
    assert issuance.writes == 1 and issuance.deletes == 0
    assert (config.read_bytes(), state.read_bytes()) == before


@pytest.mark.parametrize("failure", ["permissions", "existing"])
def test_preflight_prevents_issuance(issuance, failure):
    issuance.failure = failure
    result = issuance.invoke()
    assert result.exit_code == 1 and result.stdout == ""
    assert SECRET not in result.stderr and issuance.writes == issuance.deletes == 0


@pytest.mark.parametrize("failure", ["identity", "ownership", "timeout", "http-error", "expiry", "bad-secret", "bad-uuid", "redirect"])
def test_failed_verification_never_emits_or_replays(issuance, failure):
    issuance.failure = failure
    result = issuance.invoke()
    assert result.exit_code == 1 and result.stdout == ""
    assert SECRET not in result.stderr
    assert issuance.writes == 1 and issuance.deletes <= 1
    payload = json.loads(result.stderr.splitlines()[0])
    assert payload["emitted"] is False
    if failure in {"timeout", "http-error", "expiry", "bad-secret", "bad-uuid", "identity"}:
        assert payload["revocation_verified"] is True and issuance.key["active"] is False


@pytest.mark.parametrize("failure", ["write", "flush", "interrupt", "short-write", "rollback-redirect"])
def test_output_failure_compensates_and_reports_uncertainty(monkeypatch, issuance, failure):
    import sys
    from superset_cli import key_issuance
    original = key_issuance.emit_secret
    class Sink:
        def write(self, value):
            assert value == SECRET + "\n"
            if failure == "interrupt":
                raise KeyboardInterrupt(SECRET)
            if failure == "short-write":
                return 0
            if failure != "flush":
                raise BrokenPipeError(SECRET)
            return len(value)
        def flush(self):
            raise BrokenPipeError(SECRET)
    def broken_output(secret):
        with monkeypatch.context() as patch:
            patch.setattr(sys, "stdout", Sink())
            original(secret)
    monkeypatch.setattr(key_issuance, "emit_secret", broken_output)
    if failure == "rollback-redirect":
        issuance.failure = failure
    result = issuance.invoke()
    assert result.exit_code == 1 and SECRET not in result.stderr and result.stdout == ""
    metadata = json.loads(result.stderr.splitlines()[0])
    assert metadata["emitted"] is False and issuance.writes == issuance.deletes == 1
    assert metadata["revocation_verified"] is (failure != "rollback-redirect")
    assert "uncertain" in result.stderr.lower() or "unverified" in result.stderr.lower()


@pytest.mark.parametrize("extra", [["--operation-id", "bad"], ["--expires-on", "2030-01-01"],
    ["--expires-on", "2000-01-01T00:00:00Z"], ["--expires-on", "2099-01-01T00:00:00Z"],
    ["--server-timezone", "Not/AZone"], ["--name", ""]])
def test_bad_options_before_credentials(monkeypatch, issuance, extra):
    monkeypatch.setattr(cli, "_client", lambda **kw: pytest.fail("credentials accessed"))
    result = issuance.invoke(*extra)
    assert result.exit_code == 2 and "No such command" not in result.output
    assert not issuance.requests


def test_missing_auth_state_keeps_pipeline_empty(issuance):
    issuance.setup[2].unlink()
    result = issuance.invoke()
    assert result.exit_code == 1 and result.stdout == ""
    assert "No saved auth state" in result.stderr and not issuance.requests


def test_expiry_conversion_and_dst_folds(monkeypatch):
    from superset_cli import key_issuance
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(key_issuance, "datetime", Clock)
    body, _ = key_issuance.creation_request("Example", "2026-10-15T16:00:00+02:00", OPERATION,
                                           "sst_", "America/New_York")
    assert body["expires_on"] == "2026-10-15T10:00:00"
    with pytest.raises(ValueError):
        key_issuance.creation_request("Example", "2026-11-01T01:30:00-04:00", OPERATION,
                                     "sst_", "America/New_York")


def test_surviving_binding_is_not_replaced(issuance, monkeypatch):
    from superset_cli.config import load_config, save_config
    from superset_cli.models import APIKeySettings, AuthConfig
    config = load_config(issuance.setup[0])
    config.instances[0].auth = AuthConfig(mode="api_key", api_key=APIKeySettings(env="EXAMPLE_SUPERSET_API_KEY"))
    save_config(config, issuance.setup[0])
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", "sst_original-caller")
    before = issuance.setup[0].read_bytes()
    result = issuance.invoke()
    assert result.exit_code == 0 and result.stdout == SECRET + "\n"
    assert all(request.headers["Authorization"] == "Bearer sst_original-caller" for request in issuance.requests)
    assert issuance.setup[0].read_bytes() == before


def test_shutdown_failure_does_not_reemit_or_lose_record(monkeypatch, issuance):
    original = cli.SupersetClient.__exit__
    def interrupted(client, *args):
        original(client, *args)
        raise KeyboardInterrupt(SECRET)
    monkeypatch.setattr(cli.SupersetClient, "__exit__", interrupted)
    result = issuance.invoke()
    assert result.stdout == SECRET + "\n" and SECRET not in result.stderr
    assert issuance.writes == 1 and issuance.deletes == 0
    assert json.loads(result.stderr.splitlines()[-1])["emitted"] is True


def test_tls_before_credentials(monkeypatch, issuance):
    from superset_cli.config import load_config, save_config
    config = load_config(issuance.setup[0])
    config.instances[0].base_url = "http://superset.example.com"
    save_config(config, issuance.setup[0])
    monkeypatch.setattr(cli, "_client", lambda **kw: pytest.fail("credentials accessed"))
    result = issuance.invoke()
    assert result.exit_code == 1 and result.stdout == "" and not issuance.requests
    assert SECRET not in result.stderr


@pytest.mark.parametrize("env", [{"FORCE_COLOR": "1", "TERM": "xterm-256color"}, {"NO_COLOR": "1", "TERM": "dumb"}])
def test_create_help(env):
    result = runner.invoke(cli.app, ["auth", "api-key", "create", "--help"], env=env)
    assert result.exit_code == 0
    plain = " ".join(Text.from_ansi(result.stdout).plain.replace("│", " ").split())
    assert "Required to actually perform the write. Without it the command is a dry-run." in plain
    assert "--secret-output" in plain and "--op-vault" not in plain
