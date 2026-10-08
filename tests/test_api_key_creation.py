import copy
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
SECRET = "sst_distinctive-issuance-secret"
ITEM = "i" * 26
VAULT = "v" * 26
BASE = "/api/v1/security/api_keys/"


@pytest.fixture
def issuance(monkeypatch, instance_setup_with_session):
    class Scenario:
        failure = None
        requests = []
        processes = []
        key = None
        item = None
        deletes = 0
        writes = 0
        edits = 0

        def invoke(self, *extra, allow=True, as_json=True):
            config, state, _ = instance_setup_with_session
            args = ["--config", str(config), "auth", "api-key", "create", "prod",
                    "--name", "Example integration", "--expires-on",
                    (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                    "--operation-id", OPERATION, "--server-timezone", "UTC", "--op-account", "example", "--op-vault", "Example Vault",
                    "--state-dir", str(state), *(["--allow-write"] if allow else []),
                    *(["--json"] if as_json else []), *extra]
            result = runner.invoke(cli.app, args)
            assert SECRET not in result.output
            return result

        def http(self, request):
            self.requests.append(request)
            path = request.url.path
            if path == "/api/v1/me/roles/":
                permissions = [["can_" + permission, "ApiKey"] for permission in ("list", "create", "get", "revoke")]
                if self.failure == "permission":
                    permissions.pop()
                return httpx.Response(200, json={"result": {"userId": 7, "isActive": True,
                    "roles": {"Provisioner": permissions + [["can_read", "SecurityRestApi"]]}}})
            if path.endswith("csrf_token/"):
                return httpx.Response(200, json={"result": "csrf"})
            if request.method == "POST":
                assert request.headers["X-CSRFToken"] == "csrf"
                self.writes += 1
                body = json.loads(request.content)
                assert body["expires_on"] and OPERATION in body["name"]
                assert datetime.fromisoformat(body["expires_on"]).tzinfo is None
                if self.failure and self.failure.startswith("status-"):
                    return httpx.Response(int(self.failure.split("-")[1]), json={"message": SECRET})
                if self.failure != "late-create":
                    self.key = {"uuid": KEY_UUID, "name": body["name"], "active": True,
                                "expires_on": body["expires_on"], "revoked_on": None}
                if self.failure in {"post-timeout", "late-create"}:
                    raise httpx.ReadTimeout(SECRET, request=request)
                response = {**self.key, "key": SECRET, "key_prefix": "sst_"}
                if self.failure == "bad-issued":
                    response["uuid"] = "bad"
                if self.failure == "bad-secret":
                    response["key"] = SECRET + "\n"
                if self.failure == "post-error":
                    return httpx.Response(500, json={"message": SECRET})
                if self.failure == "expiry-mismatch":
                    self.key["expires_on"] = "2000-01-01T00:00:00"
                return httpx.Response(201, json={"result": response})
            if request.method == "DELETE":
                self.deletes += 1
                if self.failure == "rollback-redirect":
                    return httpx.Response(307, headers={"Location": BASE + KEY_UUID})
                if self.failure != "rollback":
                    self.key.update(active=False, revoked_on=datetime.now(timezone.utc).isoformat())
                return httpx.Response(200, json={"message": SECRET})
            if path == BASE:
                keys = [copy.deepcopy(self.key)] if self.key else []
                if self.failure == "existing":
                    keys = [{"uuid": KEY_UUID, "name": f"Example integration [{OPERATION}]", "active": False}]
                return httpx.Response(200, json={"result": keys})
            if path == BASE + KEY_UUID:
                return httpx.Response(200, json={"result": copy.deepcopy(self.key)})
            pytest.fail(f"Unexpected request: {request.method} {path}")

        def op(self, argv, **kwargs):
            self.processes.append((argv, kwargs))
            assert argv[0] == "op" and SECRET not in " ".join(argv)
            assert kwargs["capture_output"] and kwargs["text"] and kwargs["timeout"] > 0
            assert SECRET not in kwargs.get("env", {}).values()
            assert "EXAMPLE_SUPERSET_API_KEY" not in kwargs.get("env", {})
            if self.failure == "op-missing":
                raise FileNotFoundError(SECRET)
            if argv[1] == "--version":
                return subprocess.CompletedProcess(argv, 0, "2.33.1\n", "")
            assert "--account" in argv and "--format" in argv
            if argv[1:3] == ["vault", "get"]:
                output = {"id": VAULT}
            elif argv[1:3] == ["item", "create"]:
                self.item = json.loads(kwargs["input"])
                self.item.update(id=ITEM, vault={"id": VAULT})
                output = copy.deepcopy(self.item)
                if self.failure == "item-create-timeout":
                    raise subprocess.TimeoutExpired(argv, 1, output=SECRET, stderr=SECRET)
            elif argv[1:3] == ["item", "edit"]:
                self.edits += 1
                if self.failure == "preflight-edit" or (self.writes and self.failure in {"delivery", "rollback", "rollback-redirect"}):
                    return subprocess.CompletedProcess(argv, 1, SECRET, SECRET)
                if self.writes and self.failure == "interrupt":
                    raise KeyboardInterrupt(SECRET)
                if self.writes and self.failure == "op-signaled":
                    return subprocess.CompletedProcess(argv, -15, SECRET, SECRET)
                if self.writes and self.failure == "malformed-op":
                    return subprocess.CompletedProcess(argv, 0, SECRET, SECRET)
                self.item.update(json.loads(kwargs["input"]))
                output = copy.deepcopy(self.item)
            elif argv[1:3] == ["item", "get"]:
                assert argv[3] == ITEM and "--vault" in argv and "--reveal" in argv
                output = copy.deepcopy(self.item)
                if self.failure == "deadline" and self.edits and not self.writes:
                    from superset_cli import key_issuance
                    class Clock(datetime):
                        @classmethod
                        def now(cls, tz=None):
                            return (datetime.now(timezone.utc) + timedelta(days=91)).astimezone(tz)
                    monkeypatch.setattr(key_issuance, "datetime", Clock)
                if self.writes and self.failure == "read-timeout":
                    raise subprocess.TimeoutExpired(argv, 1, output=SECRET, stderr=SECRET)
                if self.writes and self.failure == "mismatch":
                    next(field for field in output["fields"] if field["id"] == "credential")["value"] = "wrong"
                if self.writes and self.failure == "wrong-vault":
                    output["vault"]["id"] = "w" * 26
                if self.writes and self.failure == "unconcealed":
                    next(field for field in output["fields"] if field["id"] == "credential")["type"] = "STRING"
            elif argv[1:3] == ["item", "delete"]:
                self.item = None
                output = {}
            else:
                pytest.fail(f"Unexpected op command: {argv}")
            return subprocess.CompletedProcess(argv, 0, json.dumps(output), SECRET)

    scenario = Scenario()
    scenario.setup = instance_setup_with_session
    monkeypatch.setenv("EXAMPLE_SUPERSET_API_KEY", "sst_provisioner-secret")
    monkeypatch.setattr(httpx, "Client", lambda **kw: HTTP_CLIENT(**kw, transport=httpx.MockTransport(scenario.http)))
    monkeypatch.setattr(subprocess, "run", scenario.op)
    return scenario


def test_no_secret_files_or_auth_changes(monkeypatch, issuance):
    import io
    import tempfile
    config, _, state = issuance.setup
    before = (config.read_bytes(), state.read_bytes())
    original = io.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax"):
            pytest.fail("Issuance must not write local files")
        return original(file, mode, *args, **kwargs)

    monkeypatch.setattr(io, "open", guarded_open)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", lambda *a, **kw: pytest.fail("No temporary secret files"))
    result = issuance.invoke()
    assert result.exit_code == 0, result.output
    assert (config.read_bytes(), state.read_bytes()) == before


def test_missing_saved_state_preserves_existing_cli_error(issuance):
    issuance.setup[2].unlink()
    result = issuance.invoke()
    assert result.exit_code == 1 and "No saved auth state" in result.stdout
    assert OPERATION not in result.stdout
    assert not issuance.requests and not issuance.processes


def test_creation_requires_tls_before_credentials(monkeypatch, issuance):
    from superset_cli.config import load_config, save_config
    config = load_config(issuance.setup[0])
    config.instances[0].base_url = "http://superset.example.com"
    save_config(config, issuance.setup[0])
    monkeypatch.setattr(cli, "_client", lambda **kw: pytest.fail("Credentials must not be read over insecure transport"))
    result = issuance.invoke()
    assert result.exit_code == 1, result.output
    assert "HTTPS" in result.stderr
    output = json.loads(result.stdout)
    assert output["key_uuid"] is None and output["revocation_verified"] is None
    assert not issuance.requests and not issuance.processes


@pytest.mark.parametrize("binding", ["EXAMPLE_SUPERSET_API_KEY", "OP_SESSION_provisioner"])
def test_bound_provisioning_key_is_not_replaced_or_given_to_op(monkeypatch, issuance, binding):
    from superset_cli.config import load_config, save_config
    from superset_cli.models import AuthConfig, APIKeySettings
    config = load_config(issuance.setup[0])
    monkeypatch.setenv("OP_SESSION_provisioner", "sst_provisioner-secret")
    config.instances[0].auth = AuthConfig(mode="api_key", api_key=APIKeySettings(env=binding))
    save_config(config, issuance.setup[0])
    before = issuance.setup[0].read_bytes()
    result = issuance.invoke()
    assert result.exit_code == 0, result.output
    assert issuance.setup[0].read_bytes() == before
    assert all(request.headers["Authorization"] == "Bearer sst_provisioner-secret" for request in issuance.requests)
    assert all("sst_provisioner-secret" not in kwargs["env"].values() for _, kwargs in issuance.processes)


def test_cookie_credential_alias_is_not_given_to_op(monkeypatch, issuance):
    monkeypatch.setenv("OP_SESSION_provisioner", "abc")
    result = issuance.invoke()
    assert result.exit_code == 0, result.output
    assert all("abc" not in kwargs["env"].values() for _, kwargs in issuance.processes)


def test_readback_bypasses_local_op_cache(issuance):
    result = issuance.invoke()
    assert result.exit_code == 0, result.output
    for argv, _ in issuance.processes:
        if argv[1] != "--version":
            assert "--cache=false" in argv


def test_completed_delivery_is_not_lost_on_client_shutdown_interrupt(monkeypatch, issuance):
    original = cli.SupersetClient.__exit__
    def interrupted(client, *args):
        original(client, *args)
        raise KeyboardInterrupt(SECRET)
    monkeypatch.setattr(cli.SupersetClient, "__exit__", interrupted)
    result = issuance.invoke()
    assert result.exit_code == 0, result.output
    output = json.loads(result.stdout)
    assert output["stored"] is True and output["key_uuid"] == KEY_UUID
    assert issuance.writes == 1 and issuance.deletes == 0


@pytest.mark.parametrize("as_json", [True, False])
def test_create_delivers_only_to_stdin_and_verifies(issuance, as_json):
    result = issuance.invoke(as_json=as_json)
    assert result.exit_code == 0, result.output
    assert issuance.writes == 1 and issuance.deletes == 0
    assert issuance.edits >= 2  # destination edit permission checked before issuing
    secret_inputs = [kwargs["input"] for _, kwargs in issuance.processes if SECRET in (kwargs.get("input") or "")]
    assert len(secret_inputs) == 1
    assert KEY_UUID in result.stdout and ITEM in result.stdout
    if as_json:
        output = json.loads(result.stdout)
        assert output["stored"] is True and output["key_uuid"] == KEY_UUID
        assert output["vault_id"] == VAULT and output["item_id"] == ITEM


@pytest.mark.parametrize("failure", ["permission", "op-missing", "preflight-edit", "item-create-timeout", "existing", "deadline"])
def test_preflight_prevents_key_creation(issuance, failure):
    issuance.failure = failure
    result = issuance.invoke()
    assert result.exit_code == 1, result.output
    assert issuance.writes == issuance.deletes == 0
    output = json.loads(result.stdout)
    assert output["stored"] is False
    if failure == "item-create-timeout":
        assert output["item_cleanup"] == "unverified"
        assert "unverified" in output["outcome"]


@pytest.mark.parametrize("failure", ["delivery", "mismatch", "wrong-vault", "read-timeout", "interrupt", "post-timeout", "unconcealed", "bad-issued", "bad-secret", "post-error", "expiry-mismatch", "op-signaled", "malformed-op"])
def test_delivery_and_lost_response_failures_revoke_without_replay(issuance, failure):
    issuance.failure = failure
    result = issuance.invoke()
    assert result.exit_code == 1, result.output
    assert issuance.writes == issuance.deletes == 1
    output = json.loads(result.stdout)
    assert output["revocation_verified"] is True
    assert issuance.key["active"] is False
    assert output["operation_id"] == OPERATION


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
def test_failed_create_requests_do_not_leak_or_replay(issuance, status):
    issuance.failure = f"status-{status}"
    result = issuance.invoke()
    assert result.exit_code == 1, result.output
    assert issuance.writes == 1 and issuance.deletes == 0
    assert issuance.key is None
    assert json.loads(result.stdout)["outcome"] == "issuance_unverified"


@pytest.mark.parametrize("failure", ["rollback", "late-create", "rollback-redirect"])
def test_unknown_creation_or_cleanup_is_explicit(issuance, failure):
    issuance.failure = failure
    result = issuance.invoke()
    assert result.exit_code == 1, result.output
    output = json.loads(result.stdout)
    assert output["stored"] is False and output["revocation_verified"] is not True
    assert "unverified" in output["outcome"]
    assert output["operation_id"] == OPERATION and issuance.writes == 1
    if failure == "rollback-redirect":
        assert issuance.deletes == 1


@pytest.mark.parametrize("extra", [["--operation-id", "bad"], ["--expires-on", "2030-01-01"],
                                    ["--expires-on", "2000-01-01T00:00:00Z"], ["--name", ""],
                                    ["--op-vault", "--bad"], ["--expires-on", "2099-01-01T00:00:00Z"], ["--server-timezone", "Not/AZone"]])
def test_bad_inputs_before_all_access(monkeypatch, issuance, extra):
    monkeypatch.setattr(cli, "_client", lambda **kw: pytest.fail("credentials accessed"))
    result = issuance.invoke(*extra)
    assert result.exit_code == 2
    assert "No such command" not in result.output
    assert not issuance.requests and not issuance.processes


@pytest.mark.parametrize("zone,expected", [("UTC", "2026-10-15T14:00:00"), ("America/New_York", "2026-10-15T10:00:00")])
def test_expiry_uses_verified_native_server_clock(monkeypatch, zone, expected):
    from superset_cli import key_issuance
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(key_issuance, "datetime", Clock)
    body, _ = key_issuance.creation_request("Example", "2026-10-15T16:00:00+02:00", OPERATION,
                                           "example", "Example Vault", "sst_", zone)
    assert body["expires_on"] == expected
    with pytest.raises(ValueError):
        key_issuance.creation_request("Example", "2026-11-01T01:30:00-04:00", OPERATION,
                                     "example", "Example Vault", "sst_", "America/New_York")


def test_missing_allow_write_before_any_access(monkeypatch, issuance):
    monkeypatch.setattr(cli, "_require_instance", lambda *a, **kw: pytest.fail("config accessed"))
    result = issuance.invoke(allow=False)
    assert result.exit_code == 1 and "--allow-write" in result.output
    assert not issuance.requests and not issuance.processes


@pytest.mark.parametrize("env", [{"FORCE_COLOR": "1", "TERM": "xterm-256color"}, {"NO_COLOR": "1", "TERM": "dumb"}])
def test_create_help_guard(env):
    result = runner.invoke(cli.app, ["auth", "api-key", "create", "--help"], env=env)
    assert result.exit_code == 0
    plain = " ".join(Text.from_ansi(result.stdout).plain.replace("│", " ").split())
    assert "Required to actually perform the write. Without it the command is a dry-run." in plain
