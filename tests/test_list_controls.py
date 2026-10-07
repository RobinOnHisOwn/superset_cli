import json

import httpx
import pytest
from typer.testing import CliRunner

from superset_cli import cli
from superset_cli.client import SupersetClient

runner = CliRunner()
RESOURCES = [
    (["dashboards"], "dashboard"), (["charts"], "chart"),
    (["datasets"], "dataset"), (["databases"], "database"),
    (["annotation-layers"], "annotation_layer"), (["css-templates"], "css_template"),
    (["themes"], "theme"), (["tags"], "tag"), (["reports"], "report"),
    (["saved-queries"], "saved_query"), (["queries"], "query"), (["logs"], "log"),
    (["security", "roles"], "security/roles"),
    (["security", "users"], "security/users"),
    (["security", "rls"], "rowlevelsecurity"),
]


def invoke(setup, commands, *args):
    config, state = setup
    return runner.invoke(cli.app, ["--config", str(config), *commands, "list", "prod", "--state-dir", str(state), *args])


def transport(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(**kw, transport=httpx.MockTransport(handler)))


def metadata():
    return {"list_columns": ["id", "name", "viz_type", "dttm"], "order_columns": ["id", "name"]}


@pytest.mark.parametrize("commands,resource", RESOURCES)
@pytest.mark.parametrize("as_json", [False, True])
def test_filter_projection_and_all_are_consistent(monkeypatch, instance_setup, commands, resource, as_json):
    queries = []

    def handler(request):
        q = json.loads(request.url.params.get("q", "{}"))
        if request.url.path.endswith("/_info"):
            return httpx.Response(200, json={"filters": {"viz_type": [{"operator": "eq"}]}})
        assert request.url.path == f"/api/v1/{resource}/"
        if "keys" in q:
            return httpx.Response(200, json=metadata())
        queries.append(q)
        assert q["filters"] == [{"col": "viz_type", "opr": "eq", "value": "table"}]
        assert q["columns"] == ["name"]
        assert q["order_column"] == "id"
        page = q["page"]
        # Server caps the requested page size at two.
        ids = [1, 2] if page == 0 else [3]
        return httpx.Response(200, json={**metadata(), "count": 3, "ids": ids, "result": [{"name": f"item-{i}"} for i in ids]})

    transport(monkeypatch, handler)
    result = invoke(instance_setup, commands, "--all", "--page-size", "100", "--columns", "name",
                    "--filter", '{"col":"viz_type","opr":"eq","value":"table"}', *(["--json"] if as_json else []))
    assert result.exit_code == 0, result.output
    assert [q["page"] for q in queries] == [0, 1]
    if as_json:
        assert json.loads(result.stdout) == {"count": 3, "ids": [1, 2, 3], "result": [{"name": f"item-{i}"} for i in [1, 2, 3]]}
    else:
        assert [json.loads(line) for line in result.stdout.splitlines()] == [{"name": f"item-{i}"} for i in [1, 2, 3]]
        assert "None" not in result.output


@pytest.mark.parametrize("args", [
    ["--filter", "invalid"], ["--filter", "[]"],
    ["--filter", '{"col":"name","opr":"eq"}'],
    ["--filter", '{"col":"name","opr":"eq","value":NaN}'],
    ["--filter", '{"col":"name","opr":"eq","value":1e999}'],
    ["--filter", '{"col":"","opr":"eq","value":1}'],
    ["--filter", '{"col":"name","opr":"eq","value":1,"extra":2}'],
    ["--columns", ""], ["--columns", "id,name"],
    ["--columns", "name", "--columns", "name"],
    ["--all", "--page", "0"], ["--page", "-1"], ["--page-size", "0"],
])
def test_malformed_options_fail_before_access(monkeypatch, instance_setup, args):
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("network access"))
    monkeypatch.setattr(cli, "import_browser_cookies", lambda **kw: pytest.fail("browser access"))
    result = invoke(instance_setup, ["charts"], *args)
    assert result.exit_code == 2, result.output


@pytest.mark.parametrize("args,message", [
    (["--columns", "unknown"], "column"),
    (["--filter", '{"col":"unknown","opr":"eq","value":1}'], "filter"),
    (["--filter", '{"col":"viz_type","opr":"unknown","value":1}'], "filter"),
])
def test_resource_capability_rejection(monkeypatch, instance_setup, args, message):
    def handler(request):
        if request.url.path.endswith("/_info"):
            return httpx.Response(200, json={"filters": {"viz_type": [{"operator": "eq"}]}})
        return httpx.Response(200, json=metadata())
    transport(monkeypatch, handler)
    result = invoke(instance_setup, ["charts"], *args, "--json")
    assert result.exit_code == 1, result.output
    assert message in result.stderr.lower()
    assert result.stdout == ""


@pytest.mark.parametrize("pages,message", [
    ([{"count": 2, "ids": [1], "result": [{"id": 1}]}, {"count": 2, "ids": [], "result": []}], "empty"),
    ([{"count": 2, "ids": [1], "result": [{"id": 1}]}, {"count": 3, "ids": [2], "result": [{"id": 2}]}], "count"),
    ([{"count": 2, "ids": [1], "result": [{"id": 1}]}, {"count": 2, "ids": [1], "result": [{"id": 1}]}], "duplicate"),
    ([{"count": 1, "result": [{}]}], "identity"),
    ([{"count": True, "ids": [], "result": []}], "count"),
    ([{"count": 1, "ids": [1, 2], "result": [{"id": 1}, {"id": 2}]}], "count"),
    ([{"count": 1, "ids": [2], "result": [{"id": 1}]}], "identity"),
])
def test_all_rejects_incomplete_or_inconsistent_pages(monkeypatch, instance_setup, pages, message):
    def handler(request):
        q = json.loads(request.url.params.get("q", "{}"))
        return httpx.Response(200, json=metadata() if "keys" in q else pages[q["page"]])
    transport(monkeypatch, handler)
    result = invoke(instance_setup, ["charts"], "--all", "--json")
    assert result.exit_code == 1, result.output
    assert message in result.stderr.lower()
    assert result.stdout == ""


def test_all_empty_and_later_page_http_failure(monkeypatch, instance_setup):
    pages = [{"count": 0, "ids": [], "result": []}]
    def handler(request):
        q = json.loads(request.url.params.get("q", "{}"))
        if "keys" in q:
            return httpx.Response(200, json=metadata())
        if q["page"] >= len(pages):
            return httpx.Response(500, json={"message": "later page failed"})
        return httpx.Response(200, json=pages[q["page"]])
    transport(monkeypatch, handler)
    result = invoke(instance_setup, ["charts"], "--all", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"count": 0, "ids": [], "result": []}
    pages[:] = [{"count": 2, "ids": [1], "result": [{"id": 1}]}]
    result = invoke(instance_setup, ["charts"], "--all", "--json")
    assert result.exit_code == 1
    assert "later page failed" in result.stderr
    assert result.stdout == ""


def test_single_page_shape_and_composed_controls(monkeypatch, instance_setup):
    payload = {**metadata(), "count": 1, "ids": [7], "result": [{"name": "Table"}], "extra": "preserved"}
    queries = []
    def handler(request):
        q = json.loads(request.url.params.get("q", "{}"))
        if request.url.path.endswith("/_info"):
            return httpx.Response(200, json={"filters": {"viz_type": [{"operator": "eq"}], "dttm": [{"operator": "gt"}]}})
        if "keys" not in q:
            queries.append(q)
        return httpx.Response(200, json=payload)
    transport(monkeypatch, handler)
    result = invoke(instance_setup, ["charts"], "--page", "2", "--page-size", "4", "--search", "Table",
                    "--order-column", "name", "--order-direction", "desc", "--columns", "name",
                    "--filter", '{"col":"viz_type","opr":"eq","value":"table"}',
                    "--filter", '{"col":"dttm","opr":"gt","value":"2026-01-01"}', "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == payload
    assert queries == [{"page": 2, "page_size": 4, "columns": ["name"], "order_column": "name", "order_direction": "desc", "filters": [
        {"col": "slice_name", "opr": "ct", "value": "Table"},
        {"col": "viz_type", "opr": "eq", "value": "table"},
        {"col": "dttm", "opr": "gt", "value": "2026-01-01"},
    ]}]


def test_client_list_controls_are_not_cli_only(monkeypatch, instance_setup):
    seen = []
    def handler(request):
        q = json.loads(request.url.params.get("q", "{}"))
        if request.url.path.endswith("/_info"):
            return httpx.Response(200, json={"filters": {"viz_type": [{"operator": "eq"}]}})
        if "keys" in q:
            return httpx.Response(200, json=metadata())
        seen.append(q)
        return httpx.Response(200, json={"count": 1, "ids": [1], "result": [{"name": "Table"}]})
    transport(monkeypatch, handler)
    with SupersetClient(base_url="https://superset.example.com", storage_state_path=instance_setup[1] / "prod" / "storage-state.json") as client:
        result = client.list_charts(all_pages=True, columns=["name"], filters=[{"col": "viz_type", "opr": "eq", "value": "table"}])
    assert result["count"] == 1
    assert seen[0]["filters"][0]["value"] == "table"


@pytest.mark.parametrize("response,args", [
    ([], ["--columns", "name"]),
    ({"list_columns": None, "order_columns": None}, ["--all"]),
    ({"filters": None}, ["--filter", '{"col":"viz_type","opr":"eq","value":"table"}']),
    ({"filters": {"viz_type": ["eq"]}}, ["--filter", '{"col":"viz_type","opr":"eq","value":"table"}']),
])
def test_malformed_server_metadata_fails_closed(monkeypatch, instance_setup, response, args):
    transport(monkeypatch, lambda request: httpx.Response(200, json=response))
    result = invoke(instance_setup, ["charts"], *args, "--json")
    assert result.exit_code == 1
    assert "metadata" in result.stderr.lower()
    assert result.stdout == ""


def test_all_retains_supported_order_without_inventing_id_order(monkeypatch, instance_setup):
    seen = []
    def handler(request):
        q = json.loads(request.url.params.get("q", "{}"))
        if "keys" in q:
            return httpx.Response(200, json={"order_columns": ["name"], "list_columns": ["name"]})
        seen.append(q)
        return httpx.Response(200, json={"count": 1, "ids": [1], "result": [{"name": "Table"}]})
    transport(monkeypatch, handler)
    result = invoke(instance_setup, ["charts"], "--all", "--order-column", "name", "--order-direction", "desc", "--json")
    assert result.exit_code == 0, result.output
    assert seen[0]["order_column"] == "name"
    assert seen[0]["order_direction"] == "desc"
    seen.clear()
    result = invoke(instance_setup, ["charts"], "--all", "--json")
    assert result.exit_code == 0, result.output
    assert "order_column" not in seen[0]


@pytest.mark.parametrize("info_status,list_status,exit_code", [(404, 200, 0), (404, 400, 1), (403, 200, 1)])
def test_filters_on_resources_without_info_route(monkeypatch, instance_setup, info_status, list_status, exit_code):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/_info"):
            return httpx.Response(info_status, json={"message": "metadata unavailable"})
        q = json.loads(request.url.params["q"])
        assert q["filters"] == [{"col": "dttm", "opr": "gt", "value": "2026-01-01"}]
        return httpx.Response(list_status, json={"count": 0, "ids": [], "result": [], "message": "unsupported filter"})
    transport(monkeypatch, handler)
    result = invoke(instance_setup, ["logs"], "--filter", '{"col":"dttm","opr":"gt","value":"2026-01-01"}', "--json")
    assert result.exit_code == exit_code, result.output
    if info_status == 403:
        assert calls == ["/api/v1/log/_info"]
    else:
        assert calls == ["/api/v1/log/_info", "/api/v1/log/"]
    if exit_code:
        assert result.stdout == ""


@pytest.mark.parametrize("all_pages", [False, True])
@pytest.mark.parametrize("value", ["2026-01-01T00:00:00+00:00", "100%2B", "A&B=1", r"literal\u002b + %26 & café",
                                  1e16, -1e16, 1e-16, [{"plus": "+", "float": 1e16, "looks": "e+16"}]])
def test_generated_queries_survive_fab_json_fallback(monkeypatch, instance_setup, all_pages, value):
    from urllib.parse import parse_qs

    calls = []
    def handler(request):
        raw = request.url.params.get("q", "{}")  # Flask's first URL decode.
        q = json.loads(parse_qs("q=" + raw)["q"][0])  # FAB's JSON fallback.
        if request.url.path.endswith("/_info"):
            return httpx.Response(200, json={"filters": {"dttm": [{"operator": "gt"}]}})
        if "keys" in q:
            return httpx.Response(200, json=metadata())
        calls.append(q)
        assert q["filters"] == [
            {"col": "slice_name", "opr": "ct", "value": str(value)},
            {"col": "dttm", "opr": "gt", "value": value},
        ]
        return httpx.Response(200, json={"count": 2, "ids": [q.get("page", 0) + 1], "result": [{}]})

    transport(monkeypatch, handler)
    result = invoke(instance_setup, ["charts"], "--search", str(value),
                    "--filter", json.dumps({"col": "dttm", "opr": "gt", "value": value}),
                    *(["--all", "--page-size", "1"] if all_pages else []), "--json")
    assert result.exit_code == 0, result.output
    assert len(calls) == (2 if all_pages else 1)
