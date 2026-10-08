import copy
import json
import re
from contextvars import ContextVar
from datetime import datetime
from uuid import UUID
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
from pydantic import BaseModel, Field

from superset_cli.jwt_auth import load_jwt_state, refresh_jwt, require_jwt_tls
from superset_cli.api_key_auth import read_api_key
from superset_cli.models import APIKeySettings


HTTP_TIMEOUT: ContextVar[float] = ContextVar("superset_http_timeout", default=30.0)


class AuthExpiredError(Exception):
    pass


def format_api_error(exc: httpx.HTTPStatusError) -> str:
    """Bound server diagnostics and remove known request secrets before displaying them."""
    request, response = exc.request, exc.response
    raw = response.content[:16_384].decode("utf-8", errors="replace")
    if "text/html" in response.headers.get("Content-Type", "").lower() or re.search(r"<\s*(?:html|!doctype)", raw, re.I):
        detail = "HTML error response; inspect server logs"
    else:
        try:
            payload = json.loads(raw)
        except (ValueError, RecursionError):
            payload = None
        if isinstance(payload, dict):
            selected = {key: payload[key] for key in ("message", "error", "errors") if key in payload}
            detail = json.dumps(selected, ensure_ascii=False) if selected else ""
        else:
            detail = raw if payload is None else ""
    secrets = [value for _, value in request.url.params.multi_items()]
    secrets.extend([request.url.username, request.url.password])
    for part in request.headers.get("Cookie", "").split(";"):
        if "=" in part:
            secrets.append(part.partition("=")[2].strip())
    authorization = request.headers.get("Authorization", "")
    if authorization:
        secrets.extend([authorization, authorization.partition(" ")[2]])
    try:
        stack = [json.loads(request.content)]
    except (ValueError, httpx.RequestNotRead, RecursionError):
        stack = []
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
        elif isinstance(value, (str, int, float)):
            secrets.append(str(value))
    path = request.url.path
    for secret in sorted(set(filter(None, secrets)), key=len, reverse=True):
        detail = detail.replace(secret, "<redacted>").replace(json.dumps(secret, ensure_ascii=False)[1:-1], "<redacted>")
        path = path.replace(secret, "<redacted>")
    detail = re.sub(r'https?://[^\s"<>]+', "<url>", detail, flags=re.I)
    detail = re.sub(r'\bBearer\s+[^\s,;"<>]+', "Bearer <redacted>", detail, flags=re.I)
    detail = re.sub(
        r'''\b(cookie|authorization|password|passwd|secret|token|access_token|refresh_token|api[_-]?key|session)\b["']?\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,;}]+)''',
        r"\1=<redacted>", detail, flags=re.I,
    )
    # Drop terminal control sequences and collapse multi-line server messages.
    detail = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", detail)
    detail = " ".join("".join(c for c in detail if c.isprintable() or c.isspace()).split())[:400]
    path = "".join(c for c in path if c.isprintable())[:150]
    prefix = f"Superset API error: {request.method} {path} HTTP {response.status_code}"
    return f"{prefix}: {detail}" if detail else prefix


def build_q_params(q: dict) -> dict:
    if not q:
        return {}
    # FAB parses JSON q with parse_qs after Flask has already URL-decoded it.
    encoded = re.sub(
        r'"(?:\\.|[^"\\])*"|e\+',
        lambda match: "e" if match[0] == "e+" else match[0].replace("+", r"\u002b").replace("%", r"\u0025").replace("&", r"\u0026"),
        json.dumps(q),
    )
    return {"q": encoded}


def validate_list_columns(columns: list[str] | None) -> list[str]:
    columns = columns or []
    if (any(not isinstance(col, str) or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", col) for col in columns)
            or len(set(columns)) != len(columns)):
        raise ValueError("Columns must be unique field names; repeat --columns once per field.")
    return columns


def validate_list_filters(filters: list[dict] | None) -> list[dict]:
    filters = filters or []
    for item in filters:
        if (not isinstance(item, dict) or set(item) != {"col", "opr", "value"}
                or any(not isinstance(item[key], str) or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", item[key]) for key in ("col", "opr"))):
            raise ValueError('Each filter must be a JSON object with col, opr, and value.')
        json.dumps(item["value"], allow_nan=False)
    return filters


def parse_list_filters(values: list[str] | None) -> list[dict]:
    try:
        return validate_list_filters([json.loads(value) for value in values or []])
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError('Each filter must be finite JSON with col, opr, and value.') from exc


def build_list_params(
    *,
    page: int | None = None,
    page_size: int | None = None,
    search: str | None = None,
    search_column: str | None = None,
    order_column: str | None = None,
    order_direction: str | None = None,
    filters: list[dict] | None = None,
    columns: list[str] | None = None,
) -> dict:
    filters = validate_list_filters(filters)
    columns = validate_list_columns(columns)
    q: dict = {}
    if page is not None:
        q["page"] = page
    if page_size is not None:
        q["page_size"] = page_size
    if search and search_column is not None:
        q["filters"] = [{"col": search_column, "opr": "ct", "value": search}]
    if filters:
        q["filters"] = [*q.get("filters", []), *filters]
    if columns:
        q["columns"] = columns
    if order_column is not None:
        q["order_column"] = order_column
    if order_direction is not None:
        q["order_direction"] = order_direction
    return build_q_params(q)


class NotFoundError(Exception):
    pass


def _resolve_schema(spec: dict, node: dict, seen: tuple = ()) -> dict:
    """Resolve bounded local OpenAPI references and schema inheritance only."""
    if not isinstance(node, dict) or len(seen) > 32:
        raise ValueError("Invalid owner schema")
    if "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen:
            raise ValueError("Invalid owner schema reference")
        target = spec
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        node = _resolve_schema(spec, target, (*seen, ref))
    if "allOf" in node:
        merged = {key: value for key, value in node.items() if key != "allOf"}
        for member in node["allOf"]:
            resolved = _resolve_schema(spec, member, (*seen, "allOf"))
            previous, incoming = merged.get("properties", {}), resolved.get("properties", {})
            if (any(previous[key] != incoming[key] for key in previous.keys() & incoming.keys())
                    or any(merged[key] != resolved[key] for key in ("type", "items") if key in merged and key in resolved)):
                raise ValueError("Conflicting inherited owner schema")
            merged = {**merged, **resolved, "properties": {
                **merged.get("properties", {}), **resolved.get("properties", {})
            }}
        return merged
    return node


def _permission_pairs(value: list) -> set[tuple[str, str]]:
    if (not isinstance(value, list) or any(not isinstance(pair, list) or len(pair) != 2
            or any(not isinstance(name, str) or not name or not name.isprintable() for name in pair)
            for pair in value)):
        raise ValueError("Permissions must be explicit arrays of [permission_name, resource_name] pairs.")
    pairs = {tuple(pair) for pair in value}
    if len(pairs) != len(value):
        raise ValueError("Duplicate permission/resource pairs are not allowed.")
    return pairs


def _permission_rows(rows: list) -> list[dict]:
    if (not isinstance(rows, list) or any(not isinstance(row, dict) or type(row.get("id")) is not int
            or row["id"] < 1 for row in rows)):
        raise ValueError("Missing or malformed permission metadata; unknown is not empty.")
    _permission_pairs([[row.get("permission_name"), row.get("view_menu_name")] for row in rows])
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate permission IDs are not allowed.")
    return [{key: row[key] for key in ("id", "permission_name", "view_menu_name")} for row in rows]


class Cookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str
    expires: float | None = None


class StorageState(BaseModel):
    cookies: list[Cookie] = Field(default_factory=list)
    origins: list[dict] = Field(default_factory=list)


def load_storage_state(path: Path) -> StorageState:
    return StorageState.model_validate(json.loads(path.read_text()))


def build_cookie_header(state: StorageState) -> str:
    return "; ".join(f"{cookie.name}={cookie.value}" for cookie in state.cookies)


class SupersetClient:
    def __init__(self, *, base_url: str, storage_state_path: Path | None = None,
                 api_key: APIKeySettings | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.storage_state_path = storage_state_path
        self.api_key_mode = api_key is not None
        if self.api_key_mode:
            require_jwt_tls(self.base_url)
            key = read_api_key(api_key)
            payload = {}
        elif storage_state_path is not None:
            payload = json.loads(storage_state_path.read_text())
        else:
            raise ValueError("Saved authentication state is required.")
        self.jwt_mode = not self.api_key_mode and (storage_state_path.name == "jwt-state.json" or (isinstance(payload, dict) and payload.get("mode") == "jwt"))
        if self.api_key_mode:
            self.storage_state = StorageState()
            auth_headers = {"Authorization": f"Bearer {key}"}
        elif self.jwt_mode:
            require_jwt_tls(self.base_url)
            try:
                state = load_jwt_state(storage_state_path)
            except ValueError as exc:
                raise AuthExpiredError("Invalid JWT state. Run 'auth jwt login'.") from exc
            self.storage_state = StorageState()
            auth_headers = {"Authorization": f"Bearer {state['access_token']}"}
        else:
            self.storage_state = StorageState.model_validate(payload)
            auth_headers = {"Cookie": build_cookie_header(self.storage_state)}
        self.http = httpx.Client(
            base_url=self.base_url,
            headers={"Accept": "application/json", **auth_headers},
            follow_redirects=not (self.jwt_mode or self.api_key_mode),
            timeout=HTTP_TIMEOUT.get(),
        )
        self._csrf_token: str | None = None

    def _request_response(self, method: str, path: str, **kwargs) -> httpx.Response:
        if method != "GET":
            kwargs["follow_redirects"] = False
        response = self.http.request(method, path, **kwargs)
        if response.status_code == 401 and self.jwt_mode and method == "GET":
            try:
                state = refresh_jwt(self.http, self.storage_state_path)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 401:
                    raise
                raise AuthExpiredError("JWT refresh failed. Run 'auth jwt login'.") from exc
            except (ValueError, OSError) as exc:
                raise AuthExpiredError("Could not validate or persist JWT refresh. Run 'auth jwt login'.") from exc
            self.http.headers["Authorization"] = f"Bearer {state['access_token']}"
            response = self.http.request(method, path, **kwargs)
        return response

    @staticmethod
    def validate_api_path(path: str) -> None:
        decoded = path
        while unquote(decoded) != decoded:
            decoded = unquote(decoded)
        parts = urlsplit(decoded)
        if (not decoded.startswith("/api/v1/") or parts.scheme or parts.netloc
                or parts.fragment or "#" in decoded or "\\" in decoded
                or any(ord(c) < 32 or ord(c) == 127 for c in decoded)
                or any(p in {".", ".."} for p in parts.path.split("/"))):
            raise ValueError("PATH must be an instance-relative /api/v1/ path without traversal or fragments.")

    def request(self, method: str, path: str, *, params=None, json_body=None):
        self.validate_api_path(path)
        headers = {}
        if method != "GET":
            token = self.request("GET", "/api/v1/security/csrf_token/")["result"]
            headers = {"X-CSRFToken": token}
        response = self._request_response(method, path, params=params, json=json_body,
                                          headers=headers, follow_redirects=False)
        if response.is_redirect:
            raise AuthExpiredError("Superset redirected the API request. Sign in to the configured instance.")
        return self._handle_response(response, path=path)

    def _get(self, path: str, *, params: dict | None = None) -> dict:
        response = (self._request_response("GET", path, params=params) if self.jwt_mode
                    else self.http.get(path, params=params))
        return self._handle_response(response, path=path)

    def _get_binary(self, path: str, *, params: dict | None = None) -> tuple[bytes, str, int]:
        response = (self._request_response("GET", path, params=params, follow_redirects=False) if self.jwt_mode
                    else self.http.get(path, params=params, follow_redirects=False))
        if not response.is_success:
            self._handle_response(response, path=path)
        return response.content, response.headers.get("Content-Type", ""), response.status_code

    def export_assets(self, resource: str, ids: list[int]) -> tuple[bytes, str, int]:
        if resource not in {"dashboard", "chart", "dataset", "database"}:
            raise ValueError("Unsupported export resource.")
        if not ids or any(isinstance(pk, bool) or not isinstance(pk, int) or pk < 1 for pk in ids):
            raise ValueError("Export requires positive integer IDs.")
        return self._get_binary(f"/api/v1/{resource}/export/", params={"q": f"!({','.join(map(str, ids))})"})

    def _write_headers(self) -> dict[str, str]:
        if self._csrf_token is None:
            self._csrf_token = self._get("/api/v1/security/csrf_token/")["result"]
        return {"X-CSRFToken": self._csrf_token, "Referer": f"{self.base_url}/"}

    def _post(self, path: str, *, json_body: dict | None = None, files: dict | None = None, data: dict | None = None) -> dict:
        response = self._request_response("POST", path, json=json_body, files=files, data=data, headers=self._write_headers())
        return self._handle_response(response, path=path)

    def _put(self, path: str, *, json_body: dict | None = None) -> dict:
        response = self._request_response("PUT", path, json=json_body, headers=self._write_headers())
        return self._handle_response(response, path=path)

    def _delete(self, path: str) -> dict:
        response = self._request_response("DELETE", path, headers=self._write_headers())
        return self._handle_response(response, path=path)

    def _handle_response(self, response: httpx.Response, *, path: str) -> dict:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthExpiredError(
                    "API key rejected or expired; verify the environment binding and server capability." if self.api_key_mode else
                    "JWT expired or invalid. Run 'auth jwt login'." if self.jwt_mode else
                    "Session expired or invalid. Run 'auth login' to re-authenticate."
                ) from exc
            if exc.response.status_code == 404:
                raise NotFoundError(f"Resource not found: {path}") from exc
            raise
        if not response.content:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError:
            raise AuthExpiredError(
                "API key request returned non-JSON; verify server capability and authentication." if self.api_key_mode else
                "Unexpected non-JSON response — session may have expired. Run 'auth login' to re-authenticate."
            )

    def _require_owner_contract(self, resource: str, *, candidates: bool = False) -> None:
        if resource not in {"chart", "dashboard"}:
            raise ValueError("Unsupported owner resource")
        spec = self.get_openapi_spec()
        try:
            if candidates:
                operation = spec["paths"][f"/api/v1/{resource}/related/{{column_name}}"] ["get"]
                param = next(p for p in operation["parameters"] if p.get("name") == "q" and p.get("in") == "query")
                node = param.get("schema") or param["content"]["application/json"]["schema"]
                properties = _resolve_schema(spec, node)["properties"]
                for key, kind in (("filter", "string"), ("page", "integer"), ("page_size", "integer")):
                    if _resolve_schema(spec, properties[key]).get("type") != kind:
                        raise ValueError("Invalid related query schema")
            else:
                operation = spec["paths"][f"/api/v1/{resource}/{{pk}}"] ["put"]
                body = _resolve_schema(spec, operation["requestBody"])
                schema = _resolve_schema(spec, body["content"]["application/json"]["schema"])
                owners = _resolve_schema(spec, schema["properties"]["owners"])
                if owners.get("type") != "array" or _resolve_schema(spec, owners["items"]).get("type") != "integer":
                    raise ValueError("Invalid owner ID schema")
        except (KeyError, TypeError, AttributeError, ValueError, StopIteration, RecursionError):
            raise ValueError(
                "Unsupported owner API schema. Requires integer user owners and the documented related query, "
                "not editor/viewer subject IDs. Check the target OpenAPI and Superset version."
            ) from None

    def get_owners(self, resource: str, identifier: str) -> dict:
        if resource not in {"chart", "dashboard"}:
            raise ValueError("Unsupported owner resource")
        if not isinstance(identifier, str):
            raise ValueError("Owner identifier must be a numeric ID, UUID or dashboard slug.")
        decoded = identifier
        while unquote(decoded) != decoded:
            decoded = unquote(decoded)
        if (not decoded.strip() or decoded in {".", ".."} or any(c in decoded for c in "/\\?#")
                or any(ord(c) < 32 or ord(c) == 127 for c in decoded)):
            raise ValueError("Owner identifier must be a single numeric ID, UUID or dashboard slug, without URL syntax.")
        detail = getattr(self, f"get_{resource}")(identifier)
        owners = detail.get("owners") if isinstance(detail, dict) else None
        pk = detail.get("id") if isinstance(detail, dict) else None
        if (type(pk) is not int or pk < 1 or (decoded.isdecimal() and int(decoded) != pk)
                or not isinstance(owners, list)
                or any(not isinstance(owner, dict) or type(owner.get("id")) is not int
                       or owner["id"] < 1 for owner in owners)):
            raise ValueError("Unsupported or malformed owners field; missing owners are not an empty owner list.")
        return {"resource": resource, "id": pk, "owners": owners}

    def get_owner_candidates(self, resource: str, *, search: str | None = None,
                             page: int | None = None, page_size: int | None = None) -> dict:
        if page is not None and (type(page) is not int or page < 0):
            raise ValueError("Page must be a non-negative integer")
        if page_size is not None and (type(page_size) is not int or page_size < 1):
            raise ValueError("Page size must be a positive integer")
        self._require_owner_contract(resource, candidates=True)
        query = {key: value for key, value in (("filter", search), ("page", page), ("page_size", page_size)) if value is not None}
        payload = self._get(f"/api/v1/{resource}/related/owners", params=build_q_params(query) or None)
        if (not isinstance(payload, dict) or type(payload.get("count")) is not int or payload["count"] < 0
                or not isinstance(payload.get("result"), list)
                or any(not isinstance(owner, dict) or type(owner.get("value")) is not int
                       or owner["value"] < 1 or not isinstance(owner.get("text"), str) for owner in payload["result"])):
            raise ValueError("Unsupported owner candidate response; expected integer user IDs and names.")
        return payload

    def change_owners(self, resource: str, identifier: str, *, operation: str,
                      owner_ids: list[int] | None = None, clear: bool = False) -> dict:
        if operation not in {"set", "add", "remove"}:
            raise ValueError("Unsupported owner operation")
        if any(type(pk) is not int or pk < 1 for pk in owner_ids or []):
            raise ValueError("Owner IDs must be positive integers")
        ids = list(dict.fromkeys(owner_ids or []))
        if operation == "set":
            if bool(ids) == bool(clear):
                raise ValueError("Specify --owner-id or --clear, not both; empty replacement requires --clear.")
        elif not ids or (operation == "add" and clear):
            raise ValueError("Add/remove requires --owner-id; --clear is only for empty replacement or last-owner removal.")
        self._require_owner_contract(resource)
        current = self.get_owners(resource, identifier)
        current_ids = list(dict.fromkeys(owner["id"] for owner in current["owners"]))
        wanted = (ids if operation == "set" else list(dict.fromkeys(current_ids + ids)) if operation == "add"
                  else [pk for pk in current_ids if pk not in ids])
        if current_ids and not wanted and not clear:
            raise ValueError("Removing the last owner requires explicit --clear intent.")
        result = {**current, "operation": operation, "requested_owner_ids": wanted,
                  "write_performed": False, "verified": True, "matches_requested": True, "warning": None}
        if set(current_ids) == set(wanted):
            return result
        # ponytail: non-atomic read-modify-write; use verified server preconditions if supported in future.
        try:
            getattr(self, f"update_{resource}")(str(current["id"]), {"owners": wanted})
        except httpx.RequestError:
            result.update(owners=None, write_performed=None, verified=False, matches_requested=None,
                          warning="Owner write outcome is unknown after a network error. Inspect effective owners before retrying; do not blindly retry.")
            return result
        result["write_performed"] = True
        try:
            result.update(self.get_owners(resource, str(current["id"])))
        except (AuthExpiredError, NotFoundError, httpx.HTTPError, ValueError):
            result.update(owners=None, verified=False, matches_requested=None,
                          warning="Owner update succeeded, but effective-owner read-back failed. Inspect owners before retrying; do not blindly retry.")
            return result
        result["matches_requested"] = {owner["id"] for owner in result["owners"]} == set(wanted)
        if not result["matches_requested"]:
            result["warning"] = "Effective owners differ from requested IDs: the non-admin caller may have been retained or owners changed concurrently. Do not blindly retry."
        return result

    def list_dashboards(self, *, page: int | None = None, page_size: int | None = None,
                        search: str | None = None, order_column: str | None = None,
                        order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource("/api/v1/dashboard/", search_column="dashboard_title",
                                   page=page, page_size=page_size, search=search,
                                   order_column=order_column, order_direction=order_direction, **list_options)

    def get_dashboard(self, id_or_slug: str) -> dict:
        return self._get(f"/api/v1/dashboard/{id_or_slug}").get("result", {})

    def get_dashboard_charts(self, id_or_slug: str) -> list[dict]:
        return self._get(f"/api/v1/dashboard/{id_or_slug}/charts").get("result", [])

    def get_dashboard_datasets(self, id_or_slug: str) -> list[dict]:
        return self._get(f"/api/v1/dashboard/{id_or_slug}/datasets").get("result", [])

    def list_charts(self, *, page: int | None = None, page_size: int | None = None,
                    search: str | None = None, order_column: str | None = None,
                    order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource("/api/v1/chart/", search_column="slice_name",
                                   page=page, page_size=page_size, search=search,
                                   order_column=order_column, order_direction=order_direction, **list_options)

    def get_chart(self, id_or_uuid: str) -> dict:
        return self._get(f"/api/v1/chart/{id_or_uuid}").get("result", {})

    def get_chart_data(self, pk: str, *, time_range: str | None = None, filters: list[dict] | None = None,
                       force: bool = False) -> dict:
        if time_range is None and not filters:
            if force:
                return self._get(f"/api/v1/chart/{pk}/data/", params={"force": "true"})
            return self._get(f"/api/v1/chart/{pk}/data/")
        context = self.get_chart(pk).get("query_context")
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except json.JSONDecodeError as exc:
                raise ValueError("Saved chart query_context is invalid JSON.") from exc
        if not isinstance(context, dict) or not context.get("queries") or not isinstance(context["queries"], list):
            raise ValueError("Saved chart has no usable query_context; save it in Explore first.")
        context = copy.deepcopy(context)
        if force:
            context["force"] = True
        for query in context["queries"]:
            if not isinstance(query, dict) or not isinstance(query.get("filters", []), list):
                raise ValueError("Saved chart query_context has invalid query filters.")
            if time_range is not None:
                query["time_range"] = time_range
            if filters:
                query["filters"] = query.get("filters", []) + copy.deepcopy(filters)
        return self._post("/api/v1/chart/data", json_body=context)

    def invalidate_dataset_cache(self, dataset_ids: list[int]) -> dict:
        if not dataset_ids or any(type(pk) is not int or pk < 1 for pk in dataset_ids):
            raise ValueError("Cache invalidation requires positive integer dataset IDs.")
        ids = list(dict.fromkeys(dataset_ids))
        path = "/api/v1/cachekey/invalidate"
        spec = self.get_openapi_spec()
        try:
            body = _resolve_schema(spec, spec["paths"][path]["post"]["requestBody"])
            schema = _resolve_schema(spec, body["content"]["application/json"]["schema"])
            uids = _resolve_schema(spec, schema["properties"]["datasource_uids"])
            if uids.get("type") != "array" or _resolve_schema(spec, uids["items"]).get("type") != "string":
                raise ValueError("Invalid datasource UID schema")
        except (KeyError, TypeError, AttributeError, ValueError, RecursionError):
            raise ValueError("Unsupported cache invalidation API schema; inspect target OpenAPI and permissions.") from None
        datasource_uids = [f"{pk}__table" for pk in ids]
        try:
            response = self._post(path, json_body={"datasource_uids": datasource_uids})
        except httpx.RequestError:
            raise ValueError("Cache invalidation outcome unknown after a network error. Check server state before retrying; no automatic retry was performed.") from None
        return {"dataset_ids": ids, "datasource_uids": datasource_uids, "accepted": True,
                "eviction_verified": False, "response": response}

    def list_datasets(self, *, page: int | None = None, page_size: int | None = None,
                      search: str | None = None, order_column: str | None = None,
                      order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource("/api/v1/dataset/", search_column="table_name",
                                   page=page, page_size=page_size, search=search,
                                   order_column=order_column, order_direction=order_direction, **list_options)

    def get_dataset(self, id_or_uuid: str) -> dict:
        return self._get(f"/api/v1/dataset/{id_or_uuid}").get("result", {})

    def list_databases(self, *, page: int | None = None, page_size: int | None = None,
                       search: str | None = None, order_column: str | None = None,
                       order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource("/api/v1/database/", search_column="database_name",
                                   page=page, page_size=page_size, search=search,
                                   order_column=order_column, order_direction=order_direction, **list_options)

    def get_database(self, pk: str) -> dict:
        return self._get(f"/api/v1/database/{pk}").get("result", {})

    def get_database_schemas(self, pk: str, *, catalog: str | None = None, force: bool = False) -> list[str]:
        q: dict = {}
        if catalog is not None:
            q["catalog"] = catalog
        if force:
            q["force"] = force
        return self._get(f"/api/v1/database/{pk}/schemas/", params=build_q_params(q) or None).get("result", [])

    def get_database_tables(
        self,
        pk: str,
        *,
        schema_name: str,
        catalog_name: str | None = None,
        force: bool = False,
    ) -> dict:
        q: dict = {"schema_name": schema_name}
        if catalog_name is not None:
            q["catalog_name"] = catalog_name
        if force:
            q["force"] = force
        return self._get(f"/api/v1/database/{pk}/tables/", params=build_q_params(q) or None)

    def get_current_user(self) -> dict:
        return self._get("/api/v1/me/").get("result", {})

    def get_current_user_roles(self) -> dict:
        return self._get("/api/v1/me/roles/").get("result", {})

    def list_roles(self, *, search: str | None = None, **list_options) -> dict:
        return self._list_resource("/api/v1/security/roles/", search=search, search_column="name", **list_options)

    def get_role(self, pk: str) -> dict:
        return self._get(f"/api/v1/security/roles/{pk}").get("result", {})

    def list_permission_resources(self, **list_options) -> dict:
        return self._list_resource("/api/v1/security/permissions-resources/", **list_options)

    def get_role_permissions(self, pk: str) -> dict:
        if not isinstance(pk, str) or not re.fullmatch(r"[1-9][0-9]*", pk):
            raise ValueError("Role ID must be a positive integer.")
        payload = self._get(f"/api/v1/security/roles/{pk}/permissions/")
        return {"result": _permission_rows(payload.get("result") if isinstance(payload, dict) else None)}

    def set_role_permissions(self, pk: str, body: dict) -> dict:
        if not isinstance(pk, str) or not re.fullmatch(r"[1-9][0-9]*", pk):
            raise ValueError("Role ID must be a positive integer.")
        if (not isinstance(body, dict) or set(body) != {"expected_role_name", "expected_permissions", "permissions"}
                or not isinstance(body["expected_role_name"], str) or not body["expected_role_name"]
                or not body["expected_role_name"].isprintable()):
            raise ValueError("Specify expected_role_name, expected_permissions, and permissions explicitly.")
        expected, wanted = (_permission_pairs(body[key]) for key in ("expected_permissions", "permissions"))
        spec = self.get_openapi_spec()
        try:
            operation = spec["paths"]["/api/v1/security/roles/{role_id}/permissions"]["post"]
            request = _resolve_schema(spec, operation["requestBody"])
            schema = _resolve_schema(spec, request["content"]["application/json"]["schema"])
            ids = _resolve_schema(spec, schema["properties"]["permission_view_menu_ids"])
            if (schema.get("type") != "object" or schema.get("required") != ["permission_view_menu_ids"]
                    or ids.get("type") != "array" or _resolve_schema(spec, ids["items"]).get("type") != "integer"):
                raise ValueError("Invalid permission ID schema")
        except (KeyError, TypeError, ValueError, RecursionError) as exc:
            raise ValueError("Unsupported role-permission POST schema; inspect the target OpenAPI contract.") from exc
        metadata = self.list_permission_resources(all_pages=True)["result"]
        try:
            rows = _permission_rows([{"id": row["id"], "permission_name": row["permission"]["name"],
                                     "view_menu_name": row["view_menu"]["name"]} for row in metadata])
        except (KeyError, TypeError) as exc:
            raise ValueError("Missing or malformed permission/resource metadata.") from exc
        by_pair = {(row["permission_name"], row["view_menu_name"]): row for row in rows}
        if not (expected | wanted) <= by_pair.keys():
            raise ValueError("Requested or expected permission/resource pair is missing from target metadata.")
        requested = sorted((by_pair[pair] for pair in wanted), key=lambda row: row["id"])
        expected_ids = {by_pair[pair]["id"] for pair in expected}

        def inspect() -> list[dict]:
            role = self.get_role(pk)
            if (not isinstance(role, dict) or type(role.get("id")) is not int or role["id"] != int(pk)
                    or role.get("name") != body["expected_role_name"]):
                raise ValueError("Role identity differs from expected ID/name; refusing to adopt it.")
            return self.get_role_permissions(pk)["result"]

        current = inspect()
        if ({row["id"] for row in current} != expected_ids
                or {(row["permission_name"], row["view_menu_name"]) for row in current} != expected):
            raise ValueError("Role permission drift: current grants differ from explicit expected permissions.")
        result = {"role_id": int(pk), "role_name": body["expected_role_name"], "requested_permissions": requested,
                  "permissions": current, "write_performed": False, "verified": True,
                  "matches_requested": True, "warning": None}
        if expected == wanted:
            return result
        # Acquire CSRF before mutation: failure here means no permission POST was sent.
        headers = self._write_headers()
        # ponytail: non-atomic expected-state check; use verified server preconditions when available.
        try:
            response = self._request_response("POST", f"/api/v1/security/roles/{pk}/permissions",
                json={"permission_view_menu_ids": [row["id"] for row in requested]}, headers=headers)
            self._handle_response(response, path=f"/api/v1/security/roles/{pk}/permissions")
        except (AuthExpiredError, NotFoundError, httpx.HTTPError, ValueError):
            result.update(permissions=None, write_performed=None, verified=False, matches_requested=None,
                warning="Permission write outcome is unknown. Inspect role grants before retrying; do not blindly retry.")
            return result
        result["write_performed"] = True
        try:
            result["permissions"] = inspect()
        except (AuthExpiredError, NotFoundError, httpx.HTTPError, ValueError):
            result.update(permissions=None, verified=False, matches_requested=None,
                warning="Permission POST succeeded, but role/grant read-back failed. Inspect before retrying; do not blindly retry.")
            return result
        result["verified"] = result["matches_requested"] = sorted(result["permissions"], key=lambda row: row["id"]) == requested
        if not result["matches_requested"]:
            result["warning"] = "Stored direct role permissions differ from the requested exact set. Inspect before retrying."
        return result

    def list_users(self, *, search: str | None = None, **list_options) -> dict:
        return self._list_resource("/api/v1/security/users/", search=search, search_column="username", **list_options)

    def get_user(self, pk: str) -> dict:
        return self._get(f"/api/v1/security/users/{pk}").get("result", {})

    def list_rls_rules(self, **list_options) -> dict:
        return self._list_resource("/api/v1/rowlevelsecurity/", **list_options)

    def get_rls_rule(self, pk: str) -> dict:
        return self._get(f"/api/v1/rowlevelsecurity/{pk}").get("result", {})

    def get_explore(self, slice_id: int) -> dict:
        return self._get("/api/v1/explore/", params={"slice_id": slice_id}).get("result", {})

    def get_explore_form_data(self, key: str) -> dict:
        return self._get(f"/api/v1/explore/form_data/{key}").get("form_data", {})

    def _list_resource(
        self, path: str, *, search_column: str | None = None,
        page: int | None = None, page_size: int | None = None,
        search: str | None = None, order_column: str | None = None,
        order_direction: str | None = None, filters: list[dict] | None = None,
        columns: list[str] | None = None, all_pages: bool = False,
    ) -> dict:
        if all_pages and page is not None:
            raise ValueError("--all cannot be combined with --page.")
        if (page is not None and (type(page) is not int or page < 0)
                or page_size is not None and (type(page_size) is not int or page_size < 1)):
            raise ValueError("Page must be non-negative and page size positive.")
        params = build_list_params(page=page, page_size=page_size, search=search,
                                   search_column=search_column, order_column=order_column,
                                   order_direction=order_direction, filters=filters, columns=columns)
        if filters:
            try:
                info = self._get(f"{path.rstrip('/')}/_info", params=build_q_params({"keys": ["filters"]}))
            except NotFoundError:
                # Superset's log API omits _info; its list endpoint still validates filters.
                pass
            else:
                supported = info.get("filters") if isinstance(info, dict) else None
                if not isinstance(supported, dict):
                    raise ValueError("Invalid list filter metadata.")
                for item in filters:
                    entries = supported.get(item["col"], [])
                    if (not isinstance(entries, list)
                            or any(not isinstance(entry, dict) or not isinstance(entry.get("operator"), str) for entry in entries)):
                        raise ValueError("Invalid list filter metadata.")
                    if item["opr"] not in {entry["operator"] for entry in entries}:
                        raise ValueError(f"Unsupported list filter: {item['col']} / {item['opr']}.")
        if columns or all_pages:
            metadata = self._get(path, params=build_q_params({"page": 0, "page_size": 1, "keys": ["list_columns", "order_columns"]}))
            if not isinstance(metadata, dict) or not isinstance(metadata.get("order_columns", []), list):
                raise ValueError("Invalid list metadata.")
            supported_columns = metadata.get("list_columns")
            if columns and (not isinstance(supported_columns, list) or any(col not in supported_columns for col in columns)):
                raise ValueError("Unsupported list column selection; inspect the resource list_columns metadata.")
            if all_pages and order_column is None and "id" in metadata.get("order_columns", []):
                params = build_list_params(page_size=page_size, search=search, search_column=search_column,
                                           order_column="id", order_direction=order_direction or "asc",
                                           filters=filters, columns=columns)
        if not all_pages:
            return self._get(path, params=params or None)
        query = json.loads(params.get("q", "{}"))
        query["page_size"] = page_size or 100
        items, ids, seen = [], [], set()
        total = None
        page_index = 0
        while True:
            payload = self._get(path, params=build_q_params({**query, "page": page_index}))
            if not isinstance(payload, dict):
                raise ValueError("Invalid list page metadata.")
            count, rows = payload.get("count"), payload.get("result")
            if type(count) is not int or count < 0 or (total is not None and count != total):
                raise ValueError("List count changed or is invalid; complete traversal cannot be verified.")
            total = count
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError("Invalid list rows; complete traversal cannot be verified.")
            if not rows and len(items) < total:
                raise ValueError("Premature empty page; complete traversal cannot be verified.")
            page_ids = payload.get("ids", [row.get("id") for row in rows])
            if not isinstance(page_ids, list) or len(page_ids) != len(rows):
                raise ValueError("Missing or mismatched list identity metadata.")
            for row, pk in zip(rows, page_ids):
                if (isinstance(pk, bool) or not isinstance(pk, (str, int)) or str(pk) == ""
                        or ("id" in row and str(row["id"]) != str(pk))):
                    raise ValueError("Missing or mismatched list identity.")
                identity = str(pk)
                if identity in seen:
                    raise ValueError("Duplicate list identity; traversal made no reliable progress.")
                seen.add(identity)
            items.extend(rows)
            ids.extend(page_ids)
            if len(items) > total:
                raise ValueError("List rows exceed the reported count.")
            if len(items) == total:
                return {"count": total, "ids": ids, "result": items}
            page_index += 1

    def list_annotation_layers(self, *, page: int | None = None, page_size: int | None = None,
                               search: str | None = None, order_column: str | None = None,
                               order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource(
            "/api/v1/annotation_layer/",
            **list_options,
            search_column="name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_annotation_layer(self, pk: str) -> dict:
        return self._get(f"/api/v1/annotation_layer/{pk}").get("result", {})

    def list_css_templates(self, *, page: int | None = None, page_size: int | None = None,
                           search: str | None = None, order_column: str | None = None,
                           order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource(
            "/api/v1/css_template/",
            **list_options,
            search_column="template_name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_css_template(self, pk: str) -> dict:
        return self._get(f"/api/v1/css_template/{pk}").get("result", {})

    def list_themes(self, *, page: int | None = None, page_size: int | None = None,
                    search: str | None = None, order_column: str | None = None,
                    order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource(
            "/api/v1/theme/",
            **list_options,
            search_column="theme_name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_theme(self, pk: str) -> dict:
        return self._get(f"/api/v1/theme/{pk}").get("result", {})

    def list_tags(self, *, page: int | None = None, page_size: int | None = None,
                  search: str | None = None, order_column: str | None = None,
                  order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource(
            "/api/v1/tag/",
            **list_options,
            search_column="name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_tag(self, pk: str) -> dict:
        return self._get(f"/api/v1/tag/{pk}").get("result", {})

    def list_reports(self, *, page: int | None = None, page_size: int | None = None,
                     search: str | None = None, order_column: str | None = None,
                     order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource(
            "/api/v1/report/",
            **list_options,
            search_column="name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_report(self, pk: str) -> dict:
        return self._get(f"/api/v1/report/{pk}").get("result", {})

    def list_saved_queries(self, *, page: int | None = None, page_size: int | None = None,
                           search: str | None = None, order_column: str | None = None,
                           order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource(
            "/api/v1/saved_query/",
            **list_options,
            search_column="label",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_saved_query(self, pk: str) -> dict:
        return self._get(f"/api/v1/saved_query/{pk}").get("result", {})

    def list_queries(self, *, page: int | None = None, page_size: int | None = None,
                     search: str | None = None, order_column: str | None = None,
                     order_direction: str | None = None, **list_options) -> dict:
        return self._list_resource(
            "/api/v1/query/",
            **list_options,
            search_column="sql",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_query(self, pk: str) -> dict:
        return self._get(f"/api/v1/query/{pk}").get("result", {})

    def list_logs(self, *, page: int | None = None, page_size: int | None = None,
                  order_column: str | None = None, order_direction: str | None = None,
                  **list_options) -> dict:
        return self._list_resource(
            "/api/v1/log/",
            **list_options,
            search_column=None,
            page=page,
            page_size=page_size,
            search=None,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_log(self, pk: str) -> dict:
        return self._get(f"/api/v1/log/{pk}").get("result", {})

    def get_recent_activity(self) -> dict:
        return self._get("/api/v1/log/recent_activity/")

    def get_dashboard_embedded(self, id_or_slug: str) -> dict:
        return self._get(f"/api/v1/dashboard/{id_or_slug}/embedded").get("result", {})

    def get_permalink(self, kind: str, key: str) -> dict:
        if kind not in {"dashboard", "explore", "sqllab"}:
            raise ValueError(f"Unsupported permalink kind: {kind}")
        return self._get(f"/api/v1/{kind}/permalink/{key}")

    def get_dataset_related_objects(self, id_or_uuid: str) -> dict:
        return self._get(f"/api/v1/dataset/{id_or_uuid}/related_objects")

    def get_datasource_column_values(self, datasource_type: str, datasource_id: str, column: str) -> dict:
        return self._get(
            f"/api/v1/datasource/{datasource_type}/{datasource_id}/column/{column}/values/"
        )

    def get_openapi_spec(self) -> dict:
        return self._get("/api/v1/_openapi")

    @staticmethod
    def validate_api_key_uuid(key_uuid: str) -> str:
        try:
            return str(UUID(key_uuid))
        except (ValueError, AttributeError, TypeError):
            raise ValueError("API key identifier must be a UUID.") from None

    @staticmethod
    def _api_key_metadata(item: dict) -> dict:
        fields = {"uuid", "name", "key_prefix", "scopes", "active", "created_on",
                  "expires_on", "revoked_on", "last_used_on"}
        if not isinstance(item, dict) or any(
            value is not None and type(value) not in (str, bool)
            for key, value in item.items() if key in fields
        ):
            raise ValueError("Unsupported API-key metadata response.")
        return {key: value for key, value in item.items() if key in fields}

    def list_api_keys(self) -> dict:
        payload = self._get("/api/v1/security/api_keys/")
        if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
            raise ValueError("Unsupported API-key list response.")
        return {"result": [self._api_key_metadata(item) for item in payload["result"]]}

    def get_api_key(self, key_uuid: str) -> dict:
        key_uuid = self.validate_api_key_uuid(key_uuid)
        payload = self._get(f"/api/v1/security/api_keys/{key_uuid}")
        if not isinstance(payload, dict):
            raise ValueError("Unsupported API-key metadata response.")
        item = self._api_key_metadata(payload.get("result"))
        if item.get("uuid") != key_uuid:
            raise ValueError("API-key metadata UUID mismatch.")
        return {"result": item}

    def revoke_api_key(self, key_uuid: str) -> dict:
        key_uuid = self.validate_api_key_uuid(key_uuid)
        # Preflight ownership/read permission before a non-replayable mutation.
        self.get_api_key(key_uuid)
        try:
            self._delete(f"/api/v1/security/api_keys/{key_uuid}")
            payload = self.get_api_key(key_uuid)
            item = payload["result"]
            if item.get("active") is not False or not item.get("revoked_on"):
                raise ValueError("Missing revocation evidence.")
            datetime.fromisoformat(item["revoked_on"])
        except (AuthExpiredError, NotFoundError, httpx.HTTPError, ValueError, TypeError):
            raise ValueError(
                f"API-key revocation unverified for {key_uuid}; reconcile with an independent "
                "authorized credential before retrying. The key may already be revoked."
            ) from None
        return payload

    # ----- write methods (require CLI --allow-write per ADR 0009/0010) -----

    def create_chart(self, body: dict) -> dict:
        return self._post("/api/v1/chart/", json_body=body)

    def update_chart(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/chart/{pk}", json_body=body)

    def delete_chart(self, pk: str) -> dict:
        return self._delete(f"/api/v1/chart/{pk}")

    def favorite_chart(self, pk: str) -> dict:
        return self._post(f"/api/v1/chart/{pk}/favorites/")

    def unfavorite_chart(self, pk: str) -> dict:
        return self._delete(f"/api/v1/chart/{pk}/favorites/")

    def create_dashboard(self, body: dict) -> dict:
        return self._post("/api/v1/dashboard/", json_body=body)

    def update_dashboard(self, id_or_slug: str, body: dict) -> dict:
        return self._put(f"/api/v1/dashboard/{id_or_slug}", json_body=body)

    def delete_dashboard(self, id_or_slug: str) -> dict:
        return self._delete(f"/api/v1/dashboard/{id_or_slug}")

    def favorite_dashboard(self, id_or_slug: str) -> dict:
        return self._post(f"/api/v1/dashboard/{id_or_slug}/favorites/")

    def unfavorite_dashboard(self, id_or_slug: str) -> dict:
        return self._delete(f"/api/v1/dashboard/{id_or_slug}/favorites/")

    def copy_dashboard(self, id_or_slug: str, body: dict) -> dict:
        return self._post(f"/api/v1/dashboard/{id_or_slug}/copy/", json_body=body)

    def create_dataset(self, body: dict) -> dict:
        return self._post("/api/v1/dataset/", json_body=body)

    def update_dataset(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/dataset/{pk}", json_body=body)

    def delete_dataset(self, pk: str) -> dict:
        return self._delete(f"/api/v1/dataset/{pk}")

    def refresh_dataset(self, pk: str) -> dict:
        return self._put(f"/api/v1/dataset/{pk}/refresh")

    def create_database(self, body: dict) -> dict:
        return self._post("/api/v1/database/", json_body=body)

    def update_database(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/database/{pk}", json_body=body)

    def delete_database(self, pk: str) -> dict:
        return self._delete(f"/api/v1/database/{pk}")

    def test_database_connection(self, body: dict) -> dict:
        return self._post("/api/v1/database/test_connection", json_body=body)

    def create_saved_query(self, body: dict) -> dict:
        return self._post("/api/v1/saved_query/", json_body=body)

    def update_saved_query(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/saved_query/{pk}", json_body=body)

    def delete_saved_query(self, pk: str) -> dict:
        return self._delete(f"/api/v1/saved_query/{pk}")

    def execute_sql(self, body: dict) -> dict:
        return self._post("/api/v1/sqllab/execute/", json_body=body)

    def format_sql(self, body: dict) -> dict:
        return self._post("/api/v1/sqllab/format_sql", json_body=body)

    def estimate_sql(self, body: dict) -> dict:
        return self._post("/api/v1/sqllab/estimate", json_body=body)

    def stop_sql_query(self, body: dict) -> dict:
        return self._post("/api/v1/query/stop", json_body=body)

    def create_tag(self, body: dict) -> dict:
        return self._post("/api/v1/tag/", json_body=body)

    def update_tag(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/tag/{pk}", json_body=body)

    def delete_tag(self, pk: str) -> dict:
        return self._delete(f"/api/v1/tag/{pk}")

    def create_theme(self, body: dict) -> dict:
        return self._post("/api/v1/theme/", json_body=body)

    def update_theme(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/theme/{pk}", json_body=body)

    def delete_theme(self, pk: str) -> dict:
        return self._delete(f"/api/v1/theme/{pk}")

    def create_role(self, body: dict) -> dict:
        return self._post("/api/v1/security/roles/", json_body=body)

    def update_role(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/security/roles/{pk}", json_body=body)

    def delete_role(self, pk: str) -> dict:
        return self._delete(f"/api/v1/security/roles/{pk}")

    def create_user(self, body: dict) -> dict:
        return self._post("/api/v1/security/users/", json_body=body)

    def update_user(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/security/users/{pk}", json_body=body)

    def delete_user(self, pk: str) -> dict:
        return self._delete(f"/api/v1/security/users/{pk}")

    def create_rls_rule(self, body: dict) -> dict:
        return self._post("/api/v1/rowlevelsecurity/", json_body=body)

    def update_rls_rule(self, pk: str, body: dict) -> dict:
        return self._put(f"/api/v1/rowlevelsecurity/{pk}", json_body=body)

    def delete_rls_rule(self, pk: str) -> dict:
        return self._delete(f"/api/v1/rowlevelsecurity/{pk}")

    def import_assets(self, resource: str, *, file_path: Path, passwords: dict | None = None, overwrite: bool = False) -> dict:
        if resource not in {"dashboard", "chart", "dataset", "database", "saved_query"}:
            raise ValueError(f"Unsupported import resource: {resource}")
        path = f"/api/v1/{resource}/import/"
        data: dict = {}
        if passwords is not None:
            data["passwords"] = json.dumps(passwords)
        if overwrite:
            data["overwrite"] = "true"
        with file_path.open("rb") as fh:
            files = {"formData": (file_path.name, fh.read(), "application/zip")}
        return self._post(path, files=files, data=data or None)

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> "SupersetClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
