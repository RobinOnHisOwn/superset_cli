import json
from pathlib import Path

import httpx
from pydantic import BaseModel, Field


class AuthExpiredError(Exception):
    pass


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
        self.storage_state = load_storage_state(storage_state_path)
        self.http = httpx.Client(
            base_url=self.base_url,
            headers={
                "Cookie": build_cookie_header(self.storage_state),
                "Accept": "application/json",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    def _get(self, path: str, *, params: dict | None = None) -> dict:
        response = self.http.get(path, params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthExpiredError(
                    "Session expired or invalid. Run 'auth login' to re-authenticate."
                ) from exc
            if exc.response.status_code == 404:
                raise NotFoundError(f"Resource not found: {path}") from exc
            raise
        try:
            return response.json()
        except json.JSONDecodeError:
            raise AuthExpiredError(
                "Unexpected non-JSON response — session may have expired. Run 'auth login' to re-authenticate."
            )

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

    def get_chart_data(self, pk: str) -> dict:
        return self._get(f"/api/v1/chart/{pk}/data/")

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

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> "SupersetClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
