import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from superset_cli.client import AuthExpiredError, NotFoundError, SupersetClient, build_cookie_header, build_list_params, load_storage_state
from fakes import FakeSupersetClient


def test_load_storage_state_reads_cookies(tmp_path: Path) -> None:
    path = tmp_path / "storage-state.json"
    path.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "a", "value": "1", "domain": "example.com", "path": "/"},
                    {"name": "b", "value": "2", "domain": "example.com", "path": "/"},
                ],
                "origins": [],
            }
        )
    )

    state = load_storage_state(path)

    assert len(state.cookies) == 2
    assert state.cookies[0].name == "a"
    assert state.cookies[1].value == "2"


def test_build_cookie_header_joins_cookie_pairs(tmp_path: Path) -> None:
    path = tmp_path / "storage-state.json"
    path.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "session", "value": "abc", "domain": "example.com", "path": "/"},
                    {"name": "csrf", "value": "def", "domain": "example.com", "path": "/"},
                ],
                "origins": [],
            }
        )
    )

    header = build_cookie_header(load_storage_state(path))

    assert header == "session=abc; csrf=def"


def _write_empty_state(path: Path) -> None:
    path.write_text('{"cookies":[],"origins":[]}')


def test_superset_client_close(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    client = SupersetClient(base_url="https://example.com", storage_state_path=state_path)
    assert not client.http.is_closed
    client.close()
    assert client.http.is_closed


def test_superset_client_context_manager(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        assert not client.http.is_closed
    assert client.http.is_closed


def test_fake_client_has_close(tmp_path: Path) -> None:
    client = FakeSupersetClient(base_url="https://example.com", storage_state_path=tmp_path / "s.json")
    client.close()  # must not raise


def test_fake_client_supports_context_manager(tmp_path: Path) -> None:
    with FakeSupersetClient(base_url="https://example.com", storage_state_path=tmp_path / "s.json") as client:
        assert client is not None


def _make_response(status_code: int, content: bytes = b"", content_type: str = "application/json") -> httpx.Response:
    req = httpx.Request("GET", "https://example.com/api/test")
    resp = httpx.Response(status_code, content=content, headers={"content-type": content_type})
    resp.request = req
    return resp


def test_get_raises_auth_expired_on_401(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    resp = _make_response(401)
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            with pytest.raises(AuthExpiredError):
                client._get("/api/v1/me/")


def test_get_raises_not_found_on_404(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    resp = _make_response(404)
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            with pytest.raises(NotFoundError):
                client._get("/api/v1/dashboard/99")


def test_get_raises_auth_expired_on_non_json_response(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    resp = _make_response(200, content=b"<html>Login page</html>", content_type="text/html")
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            with pytest.raises(AuthExpiredError):
                client._get("/api/v1/me/")


def test_get_dashboard_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = {"id": 7, "dashboard_title": "Revenue", "published": True}
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_dashboard("7")
    assert result == inner


def test_get_dashboard_charts_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = [{"id": 10, "slice_name": "Revenue by Month", "viz_type": "line"}]
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_dashboard_charts("7")
    assert result == inner


def test_get_dashboard_datasets_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = [{"id": 21, "table_name": "orders", "schema": "analytics"}]
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_dashboard_datasets("7")
    assert result == inner


def test_get_chart_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = {"id": 42, "slice_name": "Revenue by Month", "viz_type": "line"}
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_chart("42")
    assert result == inner


def test_get_dataset_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = {"id": 5, "table_name": "orders", "schema": "public"}
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_dataset("5")
    assert result == inner


def test_get_database_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = {"id": 1, "database_name": "prod_warehouse", "backend": "postgresql"}
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_database("1")
    assert result == inner


def test_get_database_schemas_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = ["analytics", "public"]
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_database_schemas("31", catalog="main", force=True)
    assert result == inner


def test_get_database_tables_returns_full_payload(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = {"count": 1, "result": [{"value": "orders", "type": "table", "extra": {}}]}
    resp = _make_response(200, content=json.dumps(inner).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_database_tables("31", schema_name="analytics", catalog_name="main", force=True)
    assert result == inner


def test_get_current_user_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = {"id": 3, "username": "agent@example.com", "first_name": "Superset", "last_name": "Agent"}
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_current_user()
    assert result == inner


def test_get_current_user_roles_unwraps_result(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = {"roles": [{"id": 1, "name": "Admin"}, {"id": 2, "name": "Gamma"}]}
    resp = _make_response(200, content=json.dumps({"result": inner}).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_current_user_roles()
    assert result == inner


def test_get_openapi_spec_returns_raw_payload(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    inner = {"openapi": "3.0.0", "info": {"title": "Superset API", "version": "1.0.0"}}
    resp = _make_response(200, content=json.dumps(inner).encode())
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", return_value=resp):
            result = client.get_openapi_spec()
    assert result == inner


# --- build_list_params ---


def test_build_list_params_returns_empty_dict_when_no_args() -> None:
    assert build_list_params() == {}


def test_build_list_params_with_page_only() -> None:
    result = build_list_params(page=2)
    assert json.loads(result["q"]) == {"page": 2}


def test_build_list_params_with_page_size_only() -> None:
    result = build_list_params(page_size=25)
    assert json.loads(result["q"]) == {"page_size": 25}


def test_build_list_params_with_both() -> None:
    result = build_list_params(page=1, page_size=10)
    q = json.loads(result["q"])
    assert q == {"page": 1, "page_size": 10}


def test_build_list_params_with_search_and_ordering() -> None:
    result = build_list_params(
        page=1,
        page_size=10,
        search="Revenue",
        search_column="dashboard_title",
        order_column="dashboard_title",
        order_direction="asc",
    )
    q = json.loads(result["q"])
    assert q == {
        "page": 1,
        "page_size": 10,
        "filters": [{"col": "dashboard_title", "opr": "ct", "value": "Revenue"}],
        "order_column": "dashboard_title",
        "order_direction": "asc",
    }


def test_build_list_params_omits_empty_search() -> None:
    result = build_list_params(page=0, search="", search_column="dashboard_title")
    assert json.loads(result["q"]) == {"page": 0}


def test_build_list_params_omits_none_values() -> None:
    assert build_list_params(page=None, page_size=None) == {}


# --- CSRF for writes ---


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("_post", "/api/v1/dataset/", {"json_body": {"table_name": "orders"}}),
        ("_put", "/api/v1/dataset/7", {"json_body": {"table_name": "orders"}}),
        ("_delete", "/api/v1/dataset/7", {}),
    ],
)
def test_write_requests_send_superset_csrf_token(tmp_path: Path, method: str, path: str, kwargs: dict) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v1/security/csrf_token/":
            return httpx.Response(200, json={"result": "csrf-value"})
        return httpx.Response(200, json={"result": {"id": 7}})

    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        client.http.close()
        client.http = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(handler))
        getattr(client, method)(path, **kwargs)

    assert [request.url.path for request in requests] == ["/api/v1/security/csrf_token/", path]
    assert requests[-1].headers["X-CSRFToken"] == "csrf-value"
    assert requests[-1].headers["Referer"] == "https://example.com/"


def test_csrf_token_is_cached_for_client_lifetime(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/api/v1/security/csrf_token/":
            return httpx.Response(200, json={"result": "csrf-value"})
        return httpx.Response(200, json={})

    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        client.http.close()
        client.http = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(handler))
        client._post("/api/v1/chart/", json_body={})
        client._delete("/api/v1/chart/7")

    assert paths.count("/api/v1/security/csrf_token/") == 1


# --- _get params forwarding ---


def _capture_get(resp):
    """Returns a fake http.get that appends call kwargs to a list."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return resp

    return fake_get, calls


def test_get_forwards_params_to_http_get(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    resp = _make_response(200, content=json.dumps({"result": []}).encode())
    fake_get, calls = _capture_get(resp)
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", side_effect=fake_get):
            client._get("/api/v1/dashboard/", params={"q": '{"page":0}'})
    assert calls[0][1].get("params") == {"q": '{"page":0}'}


def test_get_without_params_passes_no_params(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    resp = _make_response(200, content=json.dumps({"result": []}).encode())
    fake_get, calls = _capture_get(resp)
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", side_effect=fake_get):
            client._get("/api/v1/dashboard/")
    assert calls[0][1].get("params") is None


# --- list_* page params ---


def _list_params_test(tmp_path, method_name, expected_search_column):
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    resp = _make_response(200, content=json.dumps({"count": 0, "result": []}).encode())
    fake_get, calls = _capture_get(resp)
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", side_effect=fake_get):
            getattr(client, method_name)(
                page=0,
                page_size=5,
                search="needle",
                order_column="id",
                order_direction="desc",
            )
    expected_q = json.dumps(
        {
            "page": 0,
            "page_size": 5,
            "filters": [{"col": expected_search_column, "opr": "ct", "value": "needle"}],
            "order_column": "id",
            "order_direction": "desc",
        }
    )
    assert calls[0][1].get("params") == {"q": expected_q}


def test_list_dashboards_sends_page_params(tmp_path: Path) -> None:
    _list_params_test(tmp_path, "list_dashboards", "dashboard_title")


def test_list_charts_sends_page_params(tmp_path: Path) -> None:
    _list_params_test(tmp_path, "list_charts", "slice_name")


def test_list_datasets_sends_page_params(tmp_path: Path) -> None:
    _list_params_test(tmp_path, "list_datasets", "table_name")


def test_list_databases_sends_page_params(tmp_path: Path) -> None:
    _list_params_test(tmp_path, "list_databases", "database_name")


def test_get_database_schemas_sends_query_params(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    resp = _make_response(200, content=json.dumps({"result": []}).encode())
    fake_get, calls = _capture_get(resp)
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", side_effect=fake_get):
            client.get_database_schemas("31", catalog="main", force=True)
    expected_q = json.dumps({"catalog": "main", "force": True})
    assert calls[0][0] == "/api/v1/database/31/schemas/"
    assert calls[0][1].get("params") == {"q": expected_q}


def test_get_database_tables_sends_query_params(tmp_path: Path) -> None:
    state_path = tmp_path / "storage-state.json"
    _write_empty_state(state_path)
    resp = _make_response(200, content=json.dumps({"count": 0, "result": []}).encode())
    fake_get, calls = _capture_get(resp)
    with SupersetClient(base_url="https://example.com", storage_state_path=state_path) as client:
        with patch.object(client.http, "get", side_effect=fake_get):
            client.get_database_tables("31", schema_name="analytics", catalog_name="main", force=True)
    expected_q = json.dumps({"schema_name": "analytics", "catalog_name": "main", "force": True})
    assert calls[0][0] == "/api/v1/database/31/tables/"
    assert calls[0][1].get("params") == {"q": expected_q}
