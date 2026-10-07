"""Cache controls exercise the real client against synthetic HTTP, never live writes."""
import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from rich.text import Text
from typer.testing import CliRunner

from superset_cli import cli
from superset_cli.client import SupersetClient

runner = CliRunner()
CONTEXT = {"datasource": {"id": 7, "type": "table"}, "queries": [
    {"filters": [{"col": "region", "op": "==", "val": "east"}], "time_range": "Last year"},
    {"filters": [], "time_range": "Last month"},
]}
RESULT = {"result": [{"status": "success", "data": [{"value": 0}], "colnames": ["value"]}]}
SPEC = {"paths": {"/api/v1/cachekey/invalidate": {"post": {"requestBody": {"content": {
    "application/json": {"schema": {"$ref": "#/components/schemas/Invalidate"}}
}}}}}, "components": {"schemas": {"Invalidate": {"type": "object", "properties": {
    "datasource_uids": {"type": "array", "items": {"type": "string"}}
}}}}}


@pytest.fixture
def api(monkeypatch, instance_setup_with_session):
    config, state_dir, _ = instance_setup_with_session
    state = SimpleNamespace(config=config, state_dir=state_dir, requests=[],
                            context=copy.deepcopy(CONTEXT), result=copy.deepcopy(RESULT),
                            spec=copy.deepcopy(SPEC), status=201, timeout=False, network=False,
                            error={"message": "Synthetic rejection"}, serialized=False)

    def handle(req):
        state.requests.append(req)
        if req.url.path == "/api/v1/_openapi":
            return httpx.Response(200, json=state.spec)
        if req.url.path == "/api/v1/security/csrf_token/":
            return httpx.Response(200, json={"result": "synthetic-csrf"})
        if req.url.path == "/api/v1/chart/7":
            context = json.dumps(state.context) if state.serialized else state.context
            return httpx.Response(200, json={"result": {"query_context": context}})
        if req.url.path == "/api/v1/cachekey/invalidate":
            if state.timeout:
                raise httpx.ReadTimeout("synthetic timeout", request=req)
            if state.network:
                raise httpx.ConnectError("synthetic error", request=req)
            return (httpx.Response(state.status) if state.status == 201
                    else httpx.Response(state.status, json=state.error))
        if req.url.path in {"/api/v1/chart/7/data/", "/api/v1/chart/data"}:
            return httpx.Response(200 if state.status == 201 else state.status,
                                  json=state.result if state.status == 201 else state.error)
        raise AssertionError(f"Unexpected request {req.method} {req.url}")

    def factory(**kwargs):
        client = SupersetClient(**kwargs)
        headers = dict(client.http.headers)
        client.http.close()
        client.http = httpx.Client(base_url=kwargs["base_url"], headers=headers,
                                   transport=httpx.MockTransport(handle))
        return client

    monkeypatch.setattr(cli, "SupersetClient", factory)
    state.factory = factory
    return state


def invoke(api, group, command, *args):
    return runner.invoke(cli.app, ["--config", str(api.config), group, command, "prod", *args,
                                  "--state-dir", str(api.state_dir)])


def test_force_saved_chart_get_and_default_parity(api):
    for args, params in [((), {}), (("--force", "--allow-write"), {"force": "true"})]:
        result = invoke(api, "charts", "data", "7", *args, "--json")
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout) == RESULT
        req = api.requests[-1]
        assert req.method == "GET" and req.url.path == "/api/v1/chart/7/data/"
        assert dict(req.url.params) == params


@pytest.mark.parametrize("serialized", [False, True])
def test_force_override_top_level_and_preserves_all_queries(api, serialized):
    api.serialized = serialized
    result = invoke(api, "charts", "data", "7", "--force", "--allow-write",
                    "--time-range", "Last week", "--filter", "region=west", "--json")
    assert result.exit_code == 0, result.output
    req = api.requests[-1]
    expected = copy.deepcopy(CONTEXT)
    expected["force"] = True
    for query in expected["queries"]:
        query["time_range"] = "Last week"
        query["filters"].append({"col": "region", "op": "==", "val": "west"})
    assert json.loads(req.content) == expected
    assert req.headers["X-CSRFToken"] == "synthetic-csrf"
    assert api.context == CONTEXT


@pytest.mark.parametrize("context", [None, "bad json", {}, {"queries": [None]}])
def test_force_overrides_missing_context_no_post(api, context):
    api.context = context
    result = invoke(api, "charts", "data", "7", "--force", "--allow-write", "--filter", "a=b")
    assert result.exit_code != 0
    assert not any(req.method == "POST" for req in api.requests)


def test_force_guard_precedes_auth_and_network(api):
    result = invoke(api, "charts", "data", "7", "--force")
    assert result.exit_code == 1 and "--allow-write" in result.output
    assert not api.requests


@pytest.mark.parametrize("metadata,fragments", [
    ({"is_cached": True, "cache_key": "key-a", "cached_dttm": "2026-01-01T00:00:00", "cache_timeout": 60},
     ["cache=hit", 'key="key-a"', 'cached_at="2026-01-01T00:00:00"', "timeout=60"]),
    ({"is_cached": False, "cache_timeout": 0}, ["cache=miss", "key=unknown", "timeout=0"]),
    ({"is_cached": False, "cache_timeout": -1}, ["cache=miss", "timeout=-1 (disabled)"]),
    ({}, ["cache=unknown", "cached_at=unknown", "timeout=unknown"]),
    ({"is_cached": None, "cache_key": None, "cached_dttm": None, "cache_timeout": None},
     ["cache=unknown", "key=null", "cached_at=null", "timeout=null"]),
])
def test_cache_diagnostics_truthful_and_opt_in(api, metadata, fragments):
    api.result["result"][0].update(metadata)
    normal = invoke(api, "charts", "data", "7")
    assert "cache=" not in normal.stdout
    result = invoke(api, "charts", "data", "7", "--cache-info")
    assert result.exit_code == 0, result.output
    for fragment in fragments:
        assert fragment in result.stdout
    assert len(api.requests) == 2  # diagnostics reuse the same response


@pytest.mark.parametrize("output", ["--json", "--csv"])
def test_cache_diagnostics_machine_output_unchanged(api, output):
    before = invoke(api, "charts", "data", "7", output)
    after = invoke(api, "charts", "data", "7", output, "--cache-info")
    assert after.exit_code == before.exit_code == 0
    assert after.stdout == before.stdout


@pytest.mark.parametrize("output", [None, "--json", "--csv"])
def test_diagnostics_multi_query_and_failure_contract(api, output):
    api.result = {"result": [{"status": "failed", "error": "Synthetic failure", "data": [], "is_cached": None},
                             {"status": "success", "data": [], "is_cached": False, "cache_key": "other"}]}
    result = invoke(api, "charts", "data", "7", "--cache-info", *([output] if output else []))
    assert result.exit_code == 1 and "0 rows" in result.output
    if output == "--json":
        assert json.loads(result.stdout) == api.result
    elif not output:
        assert "[0] cache=unknown" in result.stdout and "[1] cache=miss" in result.stdout


@pytest.mark.parametrize("json_out", [False, True])
def test_invalidation_numeric_targets_dedup_csrf_empty_201(api, json_out):
    result = invoke(api, "cache", "invalidate", "--dataset", "7", "--dataset", "8", "--dataset", "7",
                    "--allow-write", *(["--json"] if json_out else []))
    assert result.exit_code == 0, result.output
    req = api.requests[-1]
    assert req.method == "POST" and req.url.path == "/api/v1/cachekey/invalidate"
    assert json.loads(req.content) == {"datasource_uids": ["7__table", "8__table"]}
    assert req.headers["X-CSRFToken"] == "synthetic-csrf"
    assert "session=" in req.headers["Cookie"]
    if json_out:
        assert json.loads(result.stdout) == {"dataset_ids": [7, 8], "datasource_uids": ["7__table", "8__table"],
                                           "accepted": True, "eviction_verified": False, "response": {}}
    else:
        assert "accepted" in result.stdout and "not verified" in result.stdout


def test_invalidation_guard_before_requests(api):
    result = invoke(api, "cache", "invalidate", "--dataset", "7")
    assert result.exit_code == 1 and "--allow-write" in result.output and "invalidate" in result.output
    assert not api.requests


@pytest.mark.parametrize("args", [[], ["--dataset", "0"], ["--dataset", "-1"], ["--dataset", "uuid"], ["--dataset", "1.5"]])
def test_invalidation_targets_required_valid_before_requests(api, args):
    result = invoke(api, "cache", "invalidate", *args, "--allow-write")
    assert result.exit_code != 0
    assert not api.requests


@pytest.mark.parametrize("bad", [True, 0, -1, "7"])
def test_client_rejects_invalid_dataset_ids_before_access(api, bad):
    with api.factory(base_url="https://superset.example.com", storage_state_path=api.state_dir / "prod" / "storage-state.json") as client:
        with pytest.raises(ValueError, match="positive integer"):
            client.invalidate_dataset_cache([bad])
    assert not api.requests


@pytest.mark.parametrize("schema", [{}, {"type": "array", "items": {"type": "integer"}}])
def test_invalidation_schema_fails_closed(api, schema):
    api.spec["components"]["schemas"]["Invalidate"]["properties"]["datasource_uids"] = schema
    result = invoke(api, "cache", "invalidate", "--dataset", "7", "--allow-write")
    assert result.exit_code == 1 and "Unsupported cache invalidation" in result.output
    assert not any(req.method == "POST" for req in api.requests)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
def test_invalidation_failure_no_retry_or_false_success(api, status):
    api.status = status
    result = invoke(api, "cache", "invalidate", "--dataset", "7", "--allow-write", "--json")
    assert result.exit_code == 1
    assert "accepted" not in result.output
    assert sum(req.method == "POST" for req in api.requests) == 1


@pytest.mark.parametrize("failure", ["timeout", "network"])
def test_invalidation_unknown_outcome_no_retry(api, failure):
    setattr(api, failure, True)
    result = invoke(api, "cache", "invalidate", "--dataset", "7", "--allow-write")
    assert result.exit_code == 1 and "unknown" in result.output.lower()
    assert "retry" in result.output.lower()
    assert sum(req.method == "POST" for req in api.requests) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
def test_force_failures_no_retry(api, status):
    api.status = status
    result = invoke(api, "charts", "data", "7", "--force", "--allow-write", "--json")
    assert result.exit_code == 1
    assert len(api.requests) == 1


@pytest.mark.parametrize("mode", ["jwt", "api_key"])
@pytest.mark.parametrize("status", [201, 401])
def test_invalidation_bearer_auth_csrf_no_browser_or_write_replay(api, monkeypatch, mode, status, tmp_path):
    from superset_cli.models import APIKeySettings
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("No browser fallback"))
    kwargs = {"base_url": "https://superset.example.com"}
    if mode == "jwt":
        path = tmp_path / "jwt-state.json"
        path.write_text(json.dumps({"mode": "jwt", "access_token": "synthetic-access", "refresh_token": "synthetic-refresh"}))
        kwargs["storage_state_path"] = path
        expected = "Bearer synthetic-access"
    else:
        monkeypatch.setenv("EXAMPLE_CACHE_KEY", "sst_synthetic-key")
        kwargs["api_key"] = APIKeySettings(env="EXAMPLE_CACHE_KEY")
        expected = "Bearer sst_synthetic-key"
    api.status = status
    with api.factory(**kwargs) as client:
        if status == 201:
            assert client.invalidate_dataset_cache([7])["accepted"] is True
        else:
            from superset_cli.client import AuthExpiredError
            with pytest.raises(AuthExpiredError):
                client.invalidate_dataset_cache([7])
    assert sum(req.method == "POST" for req in api.requests) == 1
    for req in api.requests:
        assert req.headers["Authorization"] == expected
        assert "Cookie" not in req.headers
    assert api.requests[-1].headers["X-CSRFToken"] == "synthetic-csrf"


def test_missing_invalidation_endpoint_blocks_before_write(api):
    api.spec["paths"] = {}
    result = invoke(api, "cache", "invalidate", "--dataset", "7", "--allow-write")
    assert result.exit_code == 1 and "Unsupported" in result.output
    assert not any(req.method == "POST" for req in api.requests)


@pytest.mark.parametrize("force_color", [False, True])
def test_cache_help_explains_write_guard(monkeypatch, force_color):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR" if force_color else "NO_COLOR", "1")
    for args in [["cache", "invalidate", "--help"], ["charts", "data", "--help"]]:
        result = runner.invoke(cli.app, args)
        assert result.exit_code == 0
        if force_color:
            assert "\x1b[" in result.stdout
        help_text = Text.from_ansi(result.stdout).plain
        assert "--allow-write" in help_text and "dry-run" in help_text
