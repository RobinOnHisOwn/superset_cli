"""Transport-backed owner contracts: no live Superset or browser state."""
import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from rich.text import Text
from typer.testing import CliRunner
from superset_cli.cli import app
from superset_cli.client import SupersetClient

runner = CliRunner()
OWNER = {"id": 2, "first_name": "Example", "last_name": "Reader"}
OTHER = {"id": 3, "first_name": "Other", "last_name": "Reader"}


def spec(resource):
    return {
        "paths": {
            f"/api/v1/{resource}/{{pk}}": {
                "put": {"requestBody": {"content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/Update"}
                }}}}
            },
            f"/api/v1/{resource}/related/{{column_name}}": {
                "get": {"parameters": [{"name": "q", "in": "query", "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/Related"}}
                }}]}
            },
        },
        "components": {"schemas": {
            "Update": {"type": "object", "properties": {
                "owners": {"type": "array", "items": {"type": "integer"}}
            }},
            "Related": {"type": "object", "properties": {
                "filter": {"type": "string"}, "page": {"type": "integer"},
                "page_size": {"type": "integer"}
            }},
        }},
    }


@pytest.fixture(params=["chart", "dashboard"])
def api(request, monkeypatch, instance_setup):
    config, state_dir = instance_setup
    resource = request.param
    state = SimpleNamespace(
        resource=resource, config=config, state_dir=state_dir,
        requests=[], writes=[], owners=[copy.copy(OWNER)], schema=spec(resource),
        field="owners", detail_status=200, write_status=200, candidate_status=200,
        readback_status=200, readback_field="owners", retain_caller=False,
        detail_id=7, readback_id=7, put_timeout=False, readback_timeout=False,
        candidates={"count": 1, "result": [{"value": 3, "text": "Other Reader"}]},
    )

    def handle(req):
        state.requests.append(req)
        path = req.url.path
        if path == "/api/v1/_openapi":
            return httpx.Response(200, json=state.schema)
        if path == "/api/v1/security/csrf_token/":
            return httpx.Response(200, json={"result": "synthetic-csrf"})
        if path.endswith("/related/owners"):
            return httpx.Response(state.candidate_status, json=state.candidates)
        if req.method == "PUT":
            state.writes.append(req)
            if state.put_timeout:
                raise httpx.ReadTimeout("synthetic timeout", request=req)
            if state.write_status != 200:
                return httpx.Response(state.write_status, json={"message": "Rejected owners"})
            ids = json.loads(req.content)["owners"]
            state.owners = [{"id": pk, "first_name": "Example", "last_name": str(pk)} for pk in ids]
            if state.retain_caller and 2 not in ids:
                state.owners.append(copy.copy(OWNER))
            return httpx.Response(200, json={"result": {"owners": ids}})
        if path.startswith(f"/api/v1/{resource}/"):
            after = bool(state.writes)
            if after and state.readback_timeout:
                raise httpx.ReadTimeout("synthetic timeout", request=req)
            status = state.readback_status if after else state.detail_status
            field = state.readback_field if after else state.field
            return httpx.Response(status, json={"result": {
                "id": state.readback_id if after else state.detail_id, field: state.owners,
                "params": "unchanged", "dashboard_title": "Example"
            }})
        raise AssertionError(f"Unexpected request: {req.method} {path}")

    def factory(**kwargs):
        client = SupersetClient(**kwargs)
        headers = dict(client.http.headers)
        client.http.close()
        client.http = httpx.Client(base_url=kwargs["base_url"], headers=headers,
                                   transport=httpx.MockTransport(handle))
        return client

    monkeypatch.setattr("superset_cli.cli.SupersetClient", factory)
    return state


def invoke(api, command, *extras, json_out=True, identifier="example-identifier"):
    args = ["--config", str(api.config), api.resource + "s", command, "prod"]
    if command != "owner-candidates":
        args.append(identifier)
    args += ["--state-dir", str(api.state_dir), *extras]
    if json_out:
        args.append("--json")
    return runner.invoke(app, args)


@pytest.mark.parametrize("json_out", [True, False])
@pytest.mark.parametrize("empty", [True, False])
def test_owner_inspection(api, json_out, empty):
    api.owners = [] if empty else [OWNER, OTHER]
    result = invoke(api, "owners", json_out=json_out)
    assert result.exit_code == 0, result.output
    if json_out:
        assert json.loads(result.stdout) == {"resource": api.resource, "id": 7, "owners": api.owners}
    else:
        assert ("No owners" if empty else "Example Reader") in result.stdout


@pytest.mark.parametrize("bad", [None, [], [{"id": True}], [{"id": 0}], [{"first_name": "No ID"}], [3]])
def test_missing_or_malformed_owners_are_not_empty(api, bad):
    if bad == []:
        api.field = "editors"
    else:
        api.owners = bad
    result = invoke(api, "owners")
    assert result.exit_code == 1
    assert "owners" in result.output.lower()
    assert not api.writes


def test_candidate_query_and_envelope(api):
    result = invoke(api, "owner-candidates", "--search", "Other", "--page", "1", "--page-size", "4")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == api.candidates
    req = api.requests[-1]
    assert req.url.path == f"/api/v1/{api.resource}/related/owners"
    assert json.loads(req.url.params["q"]) == {"filter": "Other", "page": 1, "page_size": 4}


@pytest.mark.parametrize("empty", [True, False])
def test_candidates_human(api, empty):
    if empty:
        api.candidates = {"count": 0, "result": []}
    result = invoke(api, "owner-candidates", json_out=False)
    assert result.exit_code == 0, result.output
    assert ("No eligible owners" if empty else "3: Other Reader") in result.stdout


@pytest.mark.parametrize("command", ["owners-set", "owners-add", "owners-remove"])
def test_guard_before_any_requests_including_noops(api, command, monkeypatch):
    monkeypatch.setenv("SUPERSET_CLI_ALLOW_WRITE", "1")
    result = invoke(api, command, "--owner-id", "2")
    assert result.exit_code == 1, result.output
    assert "--allow-write" in result.output and "owner" in result.output
    assert not api.requests


@pytest.mark.parametrize("command,expected", [("owners-set", [3]), ("owners-add", [2, 3]), ("owners-remove", [2])])
@pytest.mark.parametrize("json_out", [True, False])
def test_mutation_only_owners_with_resolved_numeric_pk_and_readback(api, command, expected, json_out):
    if command == "owners-remove":
        api.owners = [OWNER, OTHER]
    result = invoke(api, command, "--owner-id", "3", "--owner-id", "3", "--allow-write", json_out=json_out)
    assert result.exit_code == 0, result.output
    assert len(api.writes) == 1
    assert api.writes[0].url.path == f"/api/v1/{api.resource}/7"
    assert json.loads(api.writes[0].content) == {"owners": expected}
    assert api.writes[0].headers["X-CSRFToken"] == "synthetic-csrf"
    assert api.requests[-1].url.path == f"/api/v1/{api.resource}/7"
    if json_out:
        payload = json.loads(result.stdout)
        assert payload["requested_owner_ids"] == expected
        assert payload["write_performed"] and payload["verified"] and payload["matches_requested"]
        assert [owner["id"] for owner in payload["owners"]] == expected
    else:
        assert "Effective owners" in result.stdout


@pytest.mark.parametrize("command,pk", [("owners-add", "2"), ("owners-remove", "3"), ("owners-set", "2")])
def test_opted_in_noop_does_not_put(api, command, pk):
    result = invoke(api, command, "--owner-id", pk, "--allow-write")
    assert result.exit_code == 0, result.output
    assert not api.writes
    assert json.loads(result.stdout)["write_performed"] is False


@pytest.mark.parametrize("command,extras", [
    ("owners-set", []), ("owners-set", ["--clear", "--owner-id", "2"]),
    ("owners-remove", ["--owner-id", "2"]), ("owners-add", []),
    ("owners-remove", []), ("owners-add", ["--clear", "--owner-id", "3"]),
])
def test_empty_and_clear_intent(api, command, extras):
    result = invoke(api, command, *extras, "--allow-write")
    assert result.exit_code != 0
    assert not api.writes


@pytest.mark.parametrize("command,extras", [("owners-set", []), ("owners-remove", ["--owner-id", "2"])])
def test_explicit_clear(api, command, extras):
    result = invoke(api, command, *extras, "--clear", "--allow-write")
    assert result.exit_code == 0, result.output
    assert json.loads(api.writes[0].content) == {"owners": []}


@pytest.mark.parametrize("owner_id", ["0", "-1", "abc", "1.5"])
def test_invalid_ids_do_not_write(api, owner_id):
    result = invoke(api, "owners-set", "--owner-id", owner_id, "--allow-write")
    assert result.exit_code != 0
    assert not api.writes


@pytest.mark.parametrize("json_out", [True, False])
def test_retained_caller_is_not_claimed_removed(api, json_out):
    api.retain_caller = True
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write", json_out=json_out)
    assert result.exit_code == 1, result.output
    assert len(api.writes) == 1
    assert "retained" in result.output.lower()
    if json_out:
        payload = json.loads(result.stdout)
        assert payload["write_performed"] and payload["verified"]
        assert payload["matches_requested"] is False
        assert {x["id"] for x in payload["owners"]} == {2, 3}


@pytest.mark.parametrize("status", [401, 403, 404, 422])
@pytest.mark.parametrize("json_out", [True, False])
def test_successful_put_failed_readback_is_distinct_no_retry(api, status, json_out):
    api.readback_status = status
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write", json_out=json_out)
    assert result.exit_code == 1
    assert len(api.writes) == 1
    assert "succeeded" in result.output and "read-back" in result.output
    if json_out:
        payload = json.loads(result.stdout)
        assert payload["write_performed"] is True and payload["verified"] is False
        assert payload["owners"] is None


@pytest.mark.parametrize("status", [401, 403, 404, 422])
def test_write_rejection_no_verification_or_retry(api, status):
    api.write_status = status
    result = invoke(api, "owners-set", "--owner-id", "999", "--allow-write")
    assert result.exit_code == 1
    assert len(api.writes) == 1
    assert api.requests[-1].method == "PUT"
    assert "succeeded" not in result.output


@pytest.mark.parametrize("status", [401, 403, 404])
@pytest.mark.parametrize("command", ["owners", "owner-candidates"])
def test_read_failures(api, status, command):
    api.detail_status = api.candidate_status = status
    result = invoke(api, command)
    assert result.exit_code == 1
    assert not api.writes


@pytest.mark.parametrize("change", ["editors", "string-items", "no-put", "cycle", "foreign-ref"])
def test_unsupported_put_schema_blocks_before_mutation(api, change):
    schema = api.schema["components"]["schemas"]["Update"]
    if change == "editors":
        schema["properties"] = {"editors": {"type": "array", "items": {"type": "string"}}}
    elif change == "string-items":
        schema["properties"]["owners"]["items"]["type"] = "string"
    elif change == "no-put":
        api.schema["paths"][f"/api/v1/{api.resource}/{{pk}}"] = {}
    else:
        schema.clear()
        schema["$ref"] = "#/components/schemas/Update" if change == "cycle" else "https://example.com/schema"
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write")
    assert result.exit_code == 1
    assert "unsupported" in result.output.lower()
    assert not api.writes


def test_unsupported_candidate_filter_blocks_request(api):
    api.schema["components"]["schemas"]["Related"]["properties"].pop("filter")
    result = invoke(api, "owner-candidates", "--search", "Reader")
    assert result.exit_code == 1
    assert not any(req.url.path.endswith("/related/owners") for req in api.requests)


def test_allof_and_inline_query_schema(api):
    schema = api.schema["components"]["schemas"]["Update"]
    api.schema["components"]["schemas"]["Update"] = {"allOf": [schema, {"type": "object"}]}
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write")
    assert result.exit_code == 0, result.output
    param = api.schema["paths"][f"/api/v1/{api.resource}/related/{{column_name}}"] ["get"]["parameters"][0]
    param["schema"] = param.pop("content")["application/json"]["schema"]
    result = invoke(api, "owner-candidates")
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("after", [False, True])
@pytest.mark.parametrize("identifier", ["7", "%37"])
def test_wrong_resource_id_is_not_written_or_verified(api, after, identifier):
    if after:
        api.readback_id = 8
    else:
        api.detail_id = 8
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write", identifier=identifier)
    assert result.exit_code == 1
    assert len(api.writes) == int(after)
    if after:
        assert json.loads(result.stdout)["verified"] is False


@pytest.mark.parametrize("field", ["editors", "owners"])
def test_unavailable_readback_and_timeout_are_unverified(api, field):
    if field == "editors":
        api.readback_field = field
    else:
        api.readback_timeout = True
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write")
    assert result.exit_code == 1
    assert len(api.writes) == 1
    assert json.loads(result.stdout)["verified"] is False


@pytest.mark.parametrize("json_out", [True, False])
def test_put_timeout_reports_unknown_outcome_without_retry(api, json_out):
    api.put_timeout = True
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write", json_out=json_out)
    assert result.exit_code == 1
    assert len(api.writes) == 1
    assert "no PUT" not in result.output
    if json_out:
        payload = json.loads(result.stdout)
        assert payload["write_performed"] is None and payload["verified"] is False
        assert "unknown" in payload["warning"] and "retry" in payload["warning"]
    else:
        assert "unknown" in result.output


@pytest.mark.parametrize("bad", [{}, {"count": 0, "result": None},
                                  {"count": 1, "result": [{"value": "subject-uuid", "text": "Reader"}]}])
def test_malformed_candidates_are_not_owner_ids(api, bad):
    api.candidates = bad
    result = invoke(api, "owner-candidates")
    assert result.exit_code == 1
    assert "unsupported" in result.output.lower()


def test_conflicting_allof_schemas_are_not_merged_into_supported(api):
    schema = api.schema["components"]["schemas"]["Update"]
    api.schema["components"]["schemas"]["Update"] = {"allOf": [
        {"properties": {"owners": {"type": "array", "items": {"type": "string"}}}}, schema,
    ]}
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write")
    assert result.exit_code == 1
    assert not api.writes


def test_client_rejects_bool_before_deduplication(monkeypatch):
    client = object.__new__(SupersetClient)
    monkeypatch.setattr(client, "_require_owner_contract", lambda *a, **k: None)
    monkeypatch.setattr(client, "get_owners", lambda *a: {"id": 7, "resource": "chart", "owners": [{"id": 1}]})
    with pytest.raises(ValueError, match="positive integers"):
        client.change_owners("chart", "7", operation="set", owner_ids=[1, True])


@pytest.mark.parametrize("identifier", ["7", "example-dashboard", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"])
def test_identifier_reads_and_numeric_write_resolution(api, identifier):
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write", identifier=identifier)
    assert result.exit_code == 0, result.output
    assert any(req.url.path == f"/api/v1/{api.resource}/{identifier}" for req in api.requests)
    assert api.writes[0].url.path == f"/api/v1/{api.resource}/7"


def test_default_instance_selection_for_owner_command(api):
    args = ["--config", str(api.config), api.resource + "s", "owners", "7",
            "--state-dir", str(api.state_dir), "--json"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["id"] == 7


@pytest.mark.parametrize("force_color", [False, True])
@pytest.mark.parametrize("command", ["owners-set", "owners-add", "owners-remove"])
def test_owner_mutation_help_and_clear_guard(api, command, monkeypatch, force_color):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR" if force_color else "NO_COLOR", "1")
    help_result = runner.invoke(app, [api.resource + "s", command, "--help"])
    assert help_result.exit_code == 0
    if force_color:
        assert "\x1b[" in help_result.output
    help_text = Text.from_ansi(help_result.output).plain
    assert "--allow-write" in help_text and "dry-run" in help_text
    result = invoke(api, command, "--clear")
    assert result.exit_code == 1
    assert "--allow-write" in result.output
    assert not api.requests


@pytest.mark.parametrize("param,value", [("--page", "-1"), ("--page-size", "0")])
def test_invalid_candidate_pagination_is_rejected_without_requests(api, param, value):
    result = invoke(api, "owner-candidates", param, value)
    assert result.exit_code != 0
    assert not api.requests


@pytest.mark.parametrize("conflict", ["type", "items"])
def test_nested_owner_schema_conflicts_fail_closed(api, conflict):
    good = {"type": "array", "items": {"type": "integer"}}
    bad = copy.deepcopy(good)
    if conflict == "type":
        bad["type"] = "string"
    else:
        bad["items"]["type"] = "string"
    api.schema["components"]["schemas"]["Update"]["properties"]["owners"] = {"allOf": [bad, good]}
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write")
    assert result.exit_code == 1
    assert not api.writes


@pytest.mark.parametrize("identifier", ["../dataset/7", "7?foo=bar", "7#fragment", "other/7",
                                       "%252e%252e%252fdataset%252f7", "other\\7"])
def test_owner_identifier_cannot_change_route(api, identifier):
    result = invoke(api, "owners-set", "--owner-id", "3", "--allow-write", identifier=identifier)
    assert result.exit_code == 1
    assert not api.writes
    assert all(req.url.path == "/api/v1/_openapi" for req in api.requests)
