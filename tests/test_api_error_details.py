import httpx
import pytest

from superset_cli.client import format_api_error


@pytest.mark.parametrize("status,body,content_type,expected", [
    (400, b'{"message":"The CSRF token is missing."}', "application/json", "CSRF token is missing"),
    (400, b'{"message":{"schema":["Unknown field."]}}', "application/json", "Unknown field"),
    (403, b'{"message":"Forbidden"}', "application/json", "Forbidden"),
    (502, b"upstream unavailable", "text/plain", "upstream unavailable"),
    (500, b"", "text/plain", "HTTP 500"),
    (500, b"<html>Internal server error: private traceback</html>", "text/html", "HTML error response"),
])
def test_api_error_details(status, body, content_type, expected):
    request = httpx.Request("POST", "https://superset.example.com/api/v1/chart/data?secret=private-query")
    response = httpx.Response(status, content=body, headers={"Content-Type": content_type}, request=request)
    message = format_api_error(httpx.HTTPStatusError("failure", request=request, response=response))
    assert "POST /api/v1/chart/data" in message
    assert f"HTTP {status}" in message
    assert expected in message
    assert "private-query" not in message
    assert "private traceback" not in message
    assert "superset.example.com" not in message


def test_api_error_details_redacted_and_bounded():
    request = httpx.Request("POST", "https://superset.example.com/api/v1/chart/data?token=query-secret",
                           headers={"Cookie": "session=cookie-secret", "Authorization": "Bearer bearer-secret"},
                           json={"password": "body-secret"})
    response = httpx.Response(400, request=request, json={"message":
        "Invalid request cookie-secret bearer-secret query-secret body-secret password=other-secret\n" + "x" * 1000})
    message = format_api_error(httpx.HTTPStatusError("failure", request=request, response=response))
    for secret in ["cookie-secret", "bearer-secret", "query-secret", "body-secret", "other-secret"]:
        assert secret not in message
    assert len(message) < 600
    assert "\n" not in message
