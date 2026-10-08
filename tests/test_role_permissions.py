"""Native FAB-shaped role permissions; no live instance or credentials."""
import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from rich.text import Text
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import SupersetClient

READ = ["can_read", "SecurityRestApi"]
INVALIDATE = ["can_invalidate", "CacheRestApi"]
GRANTS = [dict(id=i, permission_name=p[0], view_menu_name=p[1])
          for i, p in enumerate([READ, INVALIDATE], 1)]
SPEC = {"paths": {"/api/v1/security/roles/{role_id}/permissions": {
    "post": {"requestBody": {"content": {"application/json": {
        "schema": {"$ref": "#/components/schemas/RolePermissionPostSchema"}
    }}}}}}, "components": {"schemas": {"RolePermissionPostSchema": {
        "type": "object", "required": ["permission_view_menu_ids"],
        "properties": {"permission_view_menu_ids": {"type": "array", "items": {"type": "integer"}}}
    }}}}


@pytest.fixture
def api(monkeypatch, instance_setup):
    config, state_dir = instance_setup
    state = SimpleNamespace(config=config, state_dir=state_dir, requests=[], writes=[],
        grants=copy.deepcopy(GRANTS[:1]), role={"id": 7, "name": "CacheWorker"},
        metadata=[{"id": x["id"], "permission": {"name": x["permission_name"]},
                   "view_menu": {"name": x["view_menu_name"]}} for x in GRANTS],
        spec=copy.deepcopy(SPEC), failure=None, readback=None, rename=False, count=None)

    def handle(req):
        state.requests.append(req)
        path = req.url.path
        if path == "/api/v1/_openapi":
            return httpx.Response(200, json=state.spec)
        if path == "/api/v1/security/csrf_token/":
            return httpx.Response(200, json={"result": "synthetic-csrf"})
        if path == "/api/v1/security/permissions-resources/":
            q = json.loads(req.url.params.get("q", "{}"))
            size, page = q.get("page_size", 100), q.get("page", 0)
            return httpx.Response(200, json={"count": len(state.metadata) if state.count is None else state.count,
                "result": state.metadata[page * size:(page + 1) * size],
                "list_columns": ["id", "permission.name", "view_menu.name"], "order_columns": ["id"]})
        if path == "/api/v1/security/roles/7":
            role = {**state.role, "name": "Changed"} if state.writes and state.rename else state.role
            return httpx.Response(200, json={"result": role})
        if path == "/api/v1/security/roles/7/permissions/":
            if state.writes and state.readback == "timeout":
                raise httpx.ReadTimeout("synthetic", request=req)
            rows = state.readback if state.writes and isinstance(state.readback, list) else state.grants
            return httpx.Response(200, json={"result": rows})
        if req.method == "POST" and path == "/api/v1/security/roles/7/permissions":
            state.writes.append(req)
            assert req.headers["X-CSRFToken"] == "synthetic-csrf"
            assert json.loads(req.content) == {"permission_view_menu_ids": [2]}
            if state.failure == "timeout":
                raise httpx.ReadTimeout("synthetic", request=req)
            if isinstance(state.failure, int):
                return httpx.Response(state.failure, headers={"Location": path}, json={"message": "synthetic failure"})
            state.grants = copy.deepcopy(GRANTS[1:])
            return httpx.Response(200, json={"result": {"permission_view_menu_ids": [2]}})
        raise AssertionError(f"Unexpected request: {req.method} {path}")

    def factory(**kwargs):
        client = SupersetClient(**kwargs)
        headers = dict(client.http.headers)
        client.http.close()
        client.http = httpx.Client(base_url=kwargs["base_url"], headers=headers, transport=httpx.MockTransport(handle))
        return client

    monkeypatch.setattr("superset_cli.cli.SupersetClient", factory)
    return state


def invoke(api, command="permissions-set", *, body=None, json_out=True, allow=True, pk="7"):
    args = ["--config", str(api.config), "security", "roles", command, "prod", pk,
            "--state-dir", str(api.state_dir)]
    if command == "permissions-set":
        args += ["--body", json.dumps(body if body is not None else {
            "expected_role_name": "CacheWorker", "expected_permissions": [READ], "permissions": [INVALIDATE]})]
        if allow:
            args += ["--allow-write"]
    if json_out:
        args += ["--json"]
    return CliRunner().invoke(app, args)


@pytest.mark.parametrize("json_out", [True, False])
def test_role_permission_reads(api, json_out):
    result = invoke(api, "permissions", json_out=json_out)
    assert result.exit_code == 0, result.output
    if json_out:
        assert json.loads(result.stdout) == {"result": GRANTS[:1]}
    else:
        assert "can_read" in result.stdout and "SecurityRestApi" in result.stdout
    assert not api.writes


@pytest.mark.parametrize("json_out", [True, False])
def test_permission_metadata_discovery(api, json_out):
    result = CliRunner().invoke(app, ["--config", str(api.config), "security", "permissions", "prod",
        "--state-dir", str(api.state_dir), "--all", *(["--json"] if json_out else [])])
    assert result.exit_code == 0, result.output
    if json_out:
        assert json.loads(result.stdout)["result"] == api.metadata
    else:
        assert "can_invalidate" in result.stdout and "CacheRestApi" in result.stdout


@pytest.mark.parametrize("json_out", [True, False])
def test_exact_permission_replacement(api, json_out):
    result = invoke(api, json_out=json_out)
    assert result.exit_code == 0, result.output
    assert len(api.writes) == 1
    if json_out:
        output = json.loads(result.stdout)
        assert output["permissions"] == GRANTS[1:]
        assert output["requested_permissions"] == GRANTS[1:]
        assert output["write_performed"] is True
        assert output["verified"] is True and output["matches_requested"] is True
    else:
        assert "verified" in result.stdout.lower() and "can_invalidate" in result.stdout


def test_guard_precedes_all_access(api):
    result = invoke(api, allow=False)
    assert result.exit_code != 0 and "--allow-write" in result.output
    assert not api.requests


@pytest.mark.parametrize("change", ["name", "id", "grants", "malformed", "ambiguous", "missing", "contract", "count"])
def test_preflight_fails_closed(api, change):
    if change == "name": api.role["name"] = "Admin"
    if change == "id": api.role["id"] = 8
    if change == "grants": api.grants = copy.deepcopy(GRANTS)
    if change == "malformed": api.grants = [{}]
    if change == "ambiguous": api.metadata.append({**api.metadata[1], "id": 3})
    if change == "missing": api.metadata.pop()
    if change == "contract": api.spec = {"paths": {}}
    if change == "count": api.count = 3
    result = invoke(api)
    assert result.exit_code != 0
    assert not api.writes


@pytest.mark.parametrize("body", [{}, {"expected_role_name": "CacheWorker", "permissions": [INVALIDATE]},
    {"expected_role_name": "CacheWorker", "expected_permissions": [READ], "permissions": [[True, "CacheRestApi"]]},
    {"expected_role_name": "CacheWorker", "expected_permissions": [READ], "permissions": [INVALIDATE, INVALIDATE]}])
def test_invalid_spec(api, body):
    assert invoke(api, body=body).exit_code != 0
    assert not api.requests


@pytest.mark.parametrize("pk", ["0", "-1", "../7", "true"])
def test_invalid_role_id(api, pk):
    assert invoke(api, pk=pk).exit_code != 0
    assert not api.requests


def test_explicit_empty_initial_state(api):
    api.grants = []
    result = invoke(api, body={"expected_role_name": "CacheWorker", "expected_permissions": [], "permissions": [INVALIDATE]})
    assert result.exit_code == 0, result.output
    assert len(api.writes) == 1


def test_noop_still_requires_expected_state(api):
    api.grants = copy.deepcopy(GRANTS[1:])
    result = invoke(api, body={"expected_role_name": "CacheWorker", "expected_permissions": [INVALIDATE], "permissions": [INVALIDATE]})
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["write_performed"] is False
    assert not api.writes


@pytest.mark.parametrize("failure", ["timeout", 302, 401, 500])
def test_uncertain_mutation_never_replays(api, failure):
    api.failure = failure
    result = invoke(api)
    assert result.exit_code == 1, result.output
    output = json.loads(result.stdout)
    assert output["write_performed"] is None and output["verified"] is False
    assert "inspect" in output["warning"].lower()
    assert len(api.writes) == 1


@pytest.mark.parametrize("readback", ["timeout", [], [GRANTS[0]], [{**GRANTS[1], "id": 99}], [{}]])
def test_readback_failure_is_not_success(api, readback):
    api.readback = readback
    result = invoke(api)
    assert result.exit_code == 1, result.output
    output = json.loads(result.stdout)
    assert output["write_performed"] is True
    assert output["verified"] is False
    assert output["warning"]
    assert len(api.writes) == 1


def test_readback_role_identity_is_verified(api):
    api.rename = True
    result = invoke(api)
    assert result.exit_code == 1
    assert json.loads(result.stdout)["verified"] is False
    assert len(api.writes) == 1


@pytest.mark.parametrize("change", ["object-type", "extra-required", "malformed-required"])
def test_incompatible_request_contract(api, change):
    schema = api.spec["components"]["schemas"]["RolePermissionPostSchema"]
    if change == "object-type": schema["type"] = "string"
    if change == "extra-required": schema["required"].append("unexpected")
    if change == "malformed-required": schema["required"] = "permission_view_menu_ids"
    result = invoke(api)
    assert result.exit_code == 1
    assert "schema" in result.output.lower()
    assert not api.writes


@pytest.mark.parametrize("row", [{"id": True, "permission": {"name": "can_read"}, "view_menu": {"name": "SecurityRestApi"}},
    {"id": 1, "permission": None, "view_menu": {"name": "SecurityRestApi"}},
    {"id": 1, "permission": {"name": "can_read"}, "view_menu": {"name": "\u001b[31mResource"}}])
def test_malformed_metadata_is_not_adopted(api, row):
    api.metadata[0] = row
    assert invoke(api).exit_code == 1
    assert not api.writes


@pytest.mark.parametrize("force_color", [True, False])
def test_permission_help(monkeypatch, force_color):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR" if force_color else "NO_COLOR", "1")
    result = CliRunner().invoke(app, ["security", "roles", "permissions-set", "--help"])
    assert result.exit_code == 0
    plain = Text.from_ansi(result.stdout).plain
    assert "--allow-write" in plain
    assert "Required to actually perform the write." in plain
