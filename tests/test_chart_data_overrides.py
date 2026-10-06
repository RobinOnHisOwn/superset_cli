import json

import httpx
import pytest
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import SupersetClient
from fakes import FakeSupersetClient


@pytest.mark.parametrize("serialized", [False, True])
def test_saved_chart_query_overrides(instance_setup, serialized):
    _, state = instance_setup
    context = {"datasource": {"id": 21, "type": "table"}, "queries": [
        {"time_range": "No filter", "filters": [{"col": "active", "op": "==", "val": True}]},
        {"time_range": "No filter"},
    ]}
    seen = []
    expected_filter = {"col": "region", "op": "==", "val": "west"}

    def handle(request):
        seen.append(request)
        if request.url.path == "/api/v1/chart/10":
            return httpx.Response(200, json={"result": {"query_context": json.dumps(context) if serialized else context}})
        if request.url.path == "/api/v1/security/csrf_token/":
            return httpx.Response(200, json={"result": "synthetic-csrf"})
        assert request.method == "POST"
        assert request.url.path == "/api/v1/chart/data"
        assert request.headers["X-CSRFToken"] == "synthetic-csrf"
        body = json.loads(request.content)
        assert body["datasource"] == context["datasource"]
        assert [q["time_range"] for q in body["queries"]] == ["2026-04-01 : 2026-05-01"] * 2
        assert body["queries"][0]["filters"] == context["queries"][0]["filters"] + [expected_filter]
        assert body["queries"][1]["filters"] == [expected_filter]
        return httpx.Response(200, json={"result": [{"data": [{"value": 7}]}]})

    with SupersetClient(base_url="https://superset.example.com", storage_state_path=state / "prod" / "storage-state.json") as client:
        client.http.close()
        client.http = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(handle))
        payload = client.get_chart_data("10", time_range="2026-04-01 : 2026-05-01", filters=[expected_filter])
    assert payload["result"][0]["data"] == [{"value": 7}]
    assert len(seen) == 3
    assert context["queries"][0]["time_range"] == "No filter"


def test_chart_override_cli(monkeypatch, instance_setup):
    config, state = instance_setup
    seen = []

    def get_data(self, pk, **kwargs):
        seen.append((pk, kwargs))
        return {"result": [{"data": [{"value": 7}]}]}

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)
    monkeypatch.setattr(FakeSupersetClient, "get_chart_data", get_data)
    result = CliRunner().invoke(app, ["--config", str(config), "charts", "data", "prod", "10", "--state-dir", str(state),
                                     "--time-range", "Last week", "--filter", "region=west", "--filter", "name=a=b", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["result"][0]["data"] == [{"value": 7}]
    assert seen == [("10", {"time_range": "Last week", "filters": [
        {"col": "region", "op": "==", "val": "west"}, {"col": "name", "op": "==", "val": "a=b"}]})]


@pytest.mark.parametrize("value", ["region", "=west", "region="])
def test_chart_override_rejects_invalid_filter(instance_setup, value):
    config, state = instance_setup
    result = CliRunner().invoke(app, ["--config", str(config), "charts", "data", "prod", "10", "--state-dir", str(state),
                                     "--filter", value])
    assert result.exit_code == 2
    assert "col=value" in result.stderr


@pytest.mark.parametrize("context", [None, "not json", "null", {}, {"queries": []}, {"queries": [None]}, {"queries": [{"filters": None}]}])
def test_chart_override_requires_usable_context(instance_setup, context):
    _, state = instance_setup
    seen = []

    def handle(request):
        seen.append(request)
        return httpx.Response(200, json={"result": {"query_context": context}})

    with SupersetClient(base_url="https://superset.example.com", storage_state_path=state / "prod" / "storage-state.json") as client:
        client.http.close()
        client.http = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(handle))
        with pytest.raises(ValueError, match="query_context"):
            client.get_chart_data("10", time_range="Last week")
    assert len(seen) == 1
