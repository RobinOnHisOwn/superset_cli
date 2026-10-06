import copy
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
from pydantic import BaseModel, Field

from superset_cli.jwt_auth import load_jwt_state, refresh_jwt, require_jwt_tls


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
    return {"q": json.dumps(q)}


def build_list_params(
    *,
    page: int | None = None,
    page_size: int | None = None,
    search: str | None = None,
    search_column: str | None = None,
    order_column: str | None = None,
    order_direction: str | None = None,
) -> dict:
    q: dict = {}
    if page is not None:
        q["page"] = page
    if page_size is not None:
        q["page_size"] = page_size
    if search and search_column is not None:
        q["filters"] = [{"col": search_column, "opr": "ct", "value": search}]
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
    def __init__(self, *, base_url: str, storage_state_path: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.storage_state_path = storage_state_path
        payload = json.loads(storage_state_path.read_text())
        self.jwt_mode = storage_state_path.name == "jwt-state.json" or (isinstance(payload, dict) and payload.get("mode") == "jwt")
        if self.jwt_mode:
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
            follow_redirects=not self.jwt_mode,
            timeout=30.0,
        )
        self._csrf_token: str | None = None

    def _request_response(self, method: str, path: str, **kwargs) -> httpx.Response:
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
        response = self.http.post(path, json=json_body, files=files, data=data, headers=self._write_headers())
        return self._handle_response(response, path=path)

    def _put(self, path: str, *, json_body: dict | None = None) -> dict:
        response = self.http.put(path, json=json_body, headers=self._write_headers())
        return self._handle_response(response, path=path)

    def _delete(self, path: str) -> dict:
        response = self.http.delete(path, headers=self._write_headers())
        return self._handle_response(response, path=path)

    def _handle_response(self, response: httpx.Response, *, path: str) -> dict:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthExpiredError(
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

    def list_dashboards(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._get(
            "/api/v1/dashboard/",
            params=build_list_params(
                page=page,
                page_size=page_size,
                search=search,
                search_column="dashboard_title",
                order_column=order_column,
                order_direction=order_direction,
            )
            or None,
        )

    def get_dashboard(self, id_or_slug: str) -> dict:
        return self._get(f"/api/v1/dashboard/{id_or_slug}").get("result", {})

    def get_dashboard_charts(self, id_or_slug: str) -> list[dict]:
        return self._get(f"/api/v1/dashboard/{id_or_slug}/charts").get("result", [])

    def get_dashboard_datasets(self, id_or_slug: str) -> list[dict]:
        return self._get(f"/api/v1/dashboard/{id_or_slug}/datasets").get("result", [])

    def list_charts(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._get(
            "/api/v1/chart/",
            params=build_list_params(
                page=page,
                page_size=page_size,
                search=search,
                search_column="slice_name",
                order_column=order_column,
                order_direction=order_direction,
            )
            or None,
        )

    def get_chart(self, id_or_uuid: str) -> dict:
        return self._get(f"/api/v1/chart/{id_or_uuid}").get("result", {})

    def get_chart_data(self, pk: str, *, time_range: str | None = None, filters: list[dict] | None = None) -> dict:
        if time_range is None and not filters:
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
        for query in context["queries"]:
            if not isinstance(query, dict) or not isinstance(query.get("filters", []), list):
                raise ValueError("Saved chart query_context has invalid query filters.")
            if time_range is not None:
                query["time_range"] = time_range
            if filters:
                query["filters"] = query.get("filters", []) + copy.deepcopy(filters)
        return self._post("/api/v1/chart/data", json_body=context)

    def list_datasets(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._get(
            "/api/v1/dataset/",
            params=build_list_params(
                page=page,
                page_size=page_size,
                search=search,
                search_column="table_name",
                order_column=order_column,
                order_direction=order_direction,
            )
            or None,
        )

    def get_dataset(self, id_or_uuid: str) -> dict:
        return self._get(f"/api/v1/dataset/{id_or_uuid}").get("result", {})

    def list_databases(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._get(
            "/api/v1/database/",
            params=build_list_params(
                page=page,
                page_size=page_size,
                search=search,
                search_column="database_name",
                order_column=order_column,
                order_direction=order_direction,
            )
            or None,
        )

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

    def list_roles(self, *, search: str | None = None) -> dict:
        return self._get("/api/v1/security/roles/", params=build_list_params(search=search, search_column="name") or None)

    def get_role(self, pk: str) -> dict:
        return self._get(f"/api/v1/security/roles/{pk}").get("result", {})

    def list_users(self, *, search: str | None = None) -> dict:
        return self._get("/api/v1/security/users/", params=build_list_params(search=search, search_column="username") or None)

    def get_user(self, pk: str) -> dict:
        return self._get(f"/api/v1/security/users/{pk}").get("result", {})

    def list_rls_rules(self) -> dict:
        return self._get("/api/v1/rowlevelsecurity/")

    def get_rls_rule(self, pk: str) -> dict:
        return self._get(f"/api/v1/rowlevelsecurity/{pk}").get("result", {})

    def get_explore(self, slice_id: int) -> dict:
        return self._get("/api/v1/explore/", params={"slice_id": slice_id}).get("result", {})

    def get_explore_form_data(self, key: str) -> dict:
        return self._get(f"/api/v1/explore/form_data/{key}").get("form_data", {})

    def _list_resource(
        self,
        path: str,
        *,
        search_column: str | None,
        page: int | None,
        page_size: int | None,
        search: str | None,
        order_column: str | None,
        order_direction: str | None,
    ) -> dict:
        return self._get(
            path,
            params=build_list_params(
                page=page,
                page_size=page_size,
                search=search,
                search_column=search_column,
                order_column=order_column,
                order_direction=order_direction,
            )
            or None,
        )

    def list_annotation_layers(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._list_resource(
            "/api/v1/annotation_layer/",
            search_column="name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_annotation_layer(self, pk: str) -> dict:
        return self._get(f"/api/v1/annotation_layer/{pk}").get("result", {})

    def list_css_templates(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._list_resource(
            "/api/v1/css_template/",
            search_column="template_name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_css_template(self, pk: str) -> dict:
        return self._get(f"/api/v1/css_template/{pk}").get("result", {})

    def list_themes(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._list_resource(
            "/api/v1/theme/",
            search_column="theme_name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_theme(self, pk: str) -> dict:
        return self._get(f"/api/v1/theme/{pk}").get("result", {})

    def list_tags(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._list_resource(
            "/api/v1/tag/",
            search_column="name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_tag(self, pk: str) -> dict:
        return self._get(f"/api/v1/tag/{pk}").get("result", {})

    def list_reports(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._list_resource(
            "/api/v1/report/",
            search_column="name",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_report(self, pk: str) -> dict:
        return self._get(f"/api/v1/report/{pk}").get("result", {})

    def list_saved_queries(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._list_resource(
            "/api/v1/saved_query/",
            search_column="label",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_saved_query(self, pk: str) -> dict:
        return self._get(f"/api/v1/saved_query/{pk}").get("result", {})

    def list_queries(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._list_resource(
            "/api/v1/query/",
            search_column="sql",
            page=page,
            page_size=page_size,
            search=search,
            order_column=order_column,
            order_direction=order_direction,
        )

    def get_query(self, pk: str) -> dict:
        return self._get(f"/api/v1/query/{pk}").get("result", {})

    def list_logs(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return self._list_resource(
            "/api/v1/log/",
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
