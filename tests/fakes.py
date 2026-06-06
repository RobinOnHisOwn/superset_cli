from pathlib import Path


class FakeSupersetClient:
    def __init__(self, *, base_url: str, storage_state_path: Path) -> None:
        self.base_url = base_url
        self.storage_state_path = storage_state_path
        self.closed = False
        self.calls: list[tuple] = []

    def get_current_user(self) -> dict:
        return {
            "id": 3,
            "username": "agent@example.com",
            "first_name": "Superset",
            "last_name": "Agent",
        }

    def get_current_user_roles(self) -> dict:
        return {"roles": [{"id": 1, "name": "Admin"}, {"id": 2, "name": "Gamma"}]}

    def get_openapi_spec(self) -> dict:
        return {
            "openapi": "3.0.0",
            "info": {"title": "Superset API", "version": "1.0.0"},
        }

    def list_dashboards(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return {
            "count": 2,
            "result": [
                {"id": 7, "dashboard_title": "Revenue", "published": True},
                {"id": 8, "dashboard_title": "Ops", "published": False},
            ],
        }

    def get_dashboard(self, id_or_slug: str) -> dict:
        return {
            "id": 7,
            "slug": "revenue",
            "dashboard_title": "Revenue",
            "published": True,
        }

    def get_dashboard_charts(self, id_or_slug: str) -> list[dict]:
        return [
            {"id": 10, "slice_name": "Revenue by Month", "viz_type": "line"},
        ]

    def get_dashboard_datasets(self, id_or_slug: str) -> list[dict]:
        return [
            {"id": 21, "table_name": "orders", "schema": "analytics"},
        ]

    def list_charts(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return {
            "count": 2,
            "result": [
                {"id": 10, "slice_name": "Revenue by Month", "viz_type": "line"},
                {"id": 11, "slice_name": "Top Customers", "viz_type": "table"},
            ],
        }

    def get_chart(self, id_or_uuid: str) -> dict:
        return {
            "id": 10,
            "slice_name": "Revenue by Month",
            "viz_type": "line",
        }

    def get_chart_data(self, pk: str) -> dict:
        return {
            "result": [
                {
                    "rowcount": 2,
                    "colnames": ["month", "revenue"],
                    "data": [
                        {"month": "2026-01", "revenue": 100},
                        {"month": "2026-02", "revenue": 120},
                    ],
                }
            ]
        }

    def list_datasets(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return {
            "count": 2,
            "result": [
                {"id": 21, "table_name": "orders", "schema": "analytics"},
                {"id": 22, "table_name": "customers", "schema": None},
            ],
        }

    def get_dataset(self, id_or_uuid: str) -> dict:
        return {
            "id": 21,
            "table_name": "orders",
            "schema": "analytics",
        }

    def list_databases(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> dict:
        return {
            "count": 2,
            "result": [
                {"id": 31, "database_name": "analytics", "backend": "snowflake"},
                {"id": 32, "database_name": "warehouse", "backend": "postgresql"},
            ],
        }

    def get_database(self, pk: str) -> dict:
        return {
            "id": 31,
            "database_name": "analytics",
            "backend": "snowflake",
        }

    def get_database_schemas(self, pk: str, *, catalog: str | None = None, force: bool = False) -> list[str]:
        return ["analytics", "public"]

    def get_database_tables(
        self,
        pk: str,
        *,
        schema_name: str,
        catalog_name: str | None = None,
        force: bool = False,
    ) -> dict:
        return {
            "count": 2,
            "result": [
                {"value": "orders", "type": "table", "extra": {}},
                {"value": "customer_view", "type": "view", "extra": {}},
            ],
        }

    def list_annotation_layers(self, **kwargs) -> dict:
        return {"count": 1, "result": [{"id": 50, "name": "Earnings", "descr": "Earnings releases"}]}

    def get_annotation_layer(self, pk: str) -> dict:
        return {"id": 50, "name": "Earnings", "descr": "Earnings releases"}

    def list_css_templates(self, **kwargs) -> dict:
        return {"count": 1, "result": [{"id": 1, "template_name": "Dark"}]}

    def get_css_template(self, pk: str) -> dict:
        return {"id": 1, "template_name": "Dark"}

    def list_themes(self, **kwargs) -> dict:
        return {"count": 1, "result": [{"id": 1, "theme_name": "Default"}]}

    def get_theme(self, pk: str) -> dict:
        return {"id": 1, "theme_name": "Default"}

    def list_tags(self, **kwargs) -> dict:
        return {"count": 1, "result": [{"id": 1, "name": "finance", "type": "custom"}]}

    def get_tag(self, pk: str) -> dict:
        return {"id": 1, "name": "finance", "type": "custom"}

    def list_reports(self, **kwargs) -> dict:
        return {"count": 1, "result": [{"id": 1, "name": "Weekly", "type": "Report", "active": True}]}

    def get_report(self, pk: str) -> dict:
        return {"id": 1, "name": "Weekly", "type": "Report", "active": True}

    def list_saved_queries(self, **kwargs) -> dict:
        return {"count": 1, "result": [{"id": 1, "label": "Top customers", "schema": "analytics"}]}

    def get_saved_query(self, pk: str) -> dict:
        return {"id": 1, "label": "Top customers", "schema": "analytics"}

    def list_queries(self, **kwargs) -> dict:
        return {"count": 1, "result": [{"id": 1, "status": "success", "rows": 42, "sql": "select 1"}]}

    def get_query(self, pk: str) -> dict:
        return {"id": 1, "status": "success", "rows": 42, "sql": "select 1"}

    def list_logs(self, **kwargs) -> dict:
        return {"count": 1, "result": [{"id": 1, "action": "dashboard", "dttm": "2026-06-06T12:00:00"}]}

    def get_log(self, pk: str) -> dict:
        return {"id": 1, "action": "dashboard", "user": {"username": "alice"}, "dttm": "2026-06-06T12:00:00"}

    def get_recent_activity(self) -> dict:
        return {"result": [{"action": "dashboard", "item_title": "Revenue", "time": 1717678800000}]}

    def get_dashboard_embedded(self, id_or_slug: str) -> dict:
        return {"uuid": "abc-123", "dashboard_id": "7", "allowed_domains": ["example.com"]}

    def get_permalink(self, kind: str, key: str) -> dict:
        return {"state": {"filters": []}, "url": f"/{kind}/p/{key}"}

    def get_dataset_related_objects(self, id_or_uuid: str) -> dict:
        return {
            "charts": {"count": 1, "result": [{"id": 10, "slice_name": "Revenue by Month"}]},
            "dashboards": {"count": 1, "result": [{"id": 7, "title": "Revenue"}]},
        }

    def get_datasource_column_values(self, datasource_type: str, datasource_id: str, column: str) -> dict:
        return {"result": ["a", "b", "c"]}

    # ----- write methods (record calls only; do not mutate) -----

    def _record(self, name: str, *args, **kwargs) -> dict:
        self.calls.append((name, args, kwargs))
        return {"id": 999, "name": name, "args": list(args), "kwargs": kwargs}

    def create_chart(self, body: dict) -> dict: return self._record("create_chart", body=body)
    def update_chart(self, pk: str, body: dict) -> dict: return self._record("update_chart", pk, body=body)
    def delete_chart(self, pk: str) -> dict: return self._record("delete_chart", pk)
    def favorite_chart(self, pk: str) -> dict: return self._record("favorite_chart", pk)
    def unfavorite_chart(self, pk: str) -> dict: return self._record("unfavorite_chart", pk)

    def create_dashboard(self, body: dict) -> dict: return self._record("create_dashboard", body=body)
    def update_dashboard(self, id_or_slug: str, body: dict) -> dict: return self._record("update_dashboard", id_or_slug, body=body)
    def delete_dashboard(self, id_or_slug: str) -> dict: return self._record("delete_dashboard", id_or_slug)
    def favorite_dashboard(self, id_or_slug: str) -> dict: return self._record("favorite_dashboard", id_or_slug)
    def unfavorite_dashboard(self, id_or_slug: str) -> dict: return self._record("unfavorite_dashboard", id_or_slug)
    def copy_dashboard(self, id_or_slug: str, body: dict) -> dict: return self._record("copy_dashboard", id_or_slug, body=body)

    def create_dataset(self, body: dict) -> dict: return self._record("create_dataset", body=body)
    def update_dataset(self, pk: str, body: dict) -> dict: return self._record("update_dataset", pk, body=body)
    def delete_dataset(self, pk: str) -> dict: return self._record("delete_dataset", pk)
    def refresh_dataset(self, pk: str) -> dict: return self._record("refresh_dataset", pk)

    def create_database(self, body: dict) -> dict: return self._record("create_database", body=body)
    def update_database(self, pk: str, body: dict) -> dict: return self._record("update_database", pk, body=body)
    def delete_database(self, pk: str) -> dict: return self._record("delete_database", pk)
    def test_database_connection(self, body: dict) -> dict: return self._record("test_database_connection", body=body)

    def create_saved_query(self, body: dict) -> dict: return self._record("create_saved_query", body=body)
    def update_saved_query(self, pk: str, body: dict) -> dict: return self._record("update_saved_query", pk, body=body)
    def delete_saved_query(self, pk: str) -> dict: return self._record("delete_saved_query", pk)

    def execute_sql(self, body: dict) -> dict: return self._record("execute_sql", body=body)
    def format_sql(self, body: dict) -> dict: return self._record("format_sql", body=body)
    def estimate_sql(self, body: dict) -> dict: return self._record("estimate_sql", body=body)
    def stop_sql_query(self, body: dict) -> dict: return self._record("stop_sql_query", body=body)

    def create_tag(self, body: dict) -> dict: return self._record("create_tag", body=body)
    def update_tag(self, pk: str, body: dict) -> dict: return self._record("update_tag", pk, body=body)
    def delete_tag(self, pk: str) -> dict: return self._record("delete_tag", pk)

    def create_theme(self, body: dict) -> dict: return self._record("create_theme", body=body)
    def update_theme(self, pk: str, body: dict) -> dict: return self._record("update_theme", pk, body=body)
    def delete_theme(self, pk: str) -> dict: return self._record("delete_theme", pk)

    def create_role(self, body: dict) -> dict: return self._record("create_role", body=body)
    def update_role(self, pk: str, body: dict) -> dict: return self._record("update_role", pk, body=body)
    def delete_role(self, pk: str) -> dict: return self._record("delete_role", pk)

    def create_user(self, body: dict) -> dict: return self._record("create_user", body=body)
    def update_user(self, pk: str, body: dict) -> dict: return self._record("update_user", pk, body=body)
    def delete_user(self, pk: str) -> dict: return self._record("delete_user", pk)

    def create_rls_rule(self, body: dict) -> dict: return self._record("create_rls_rule", body=body)
    def update_rls_rule(self, pk: str, body: dict) -> dict: return self._record("update_rls_rule", pk, body=body)
    def delete_rls_rule(self, pk: str) -> dict: return self._record("delete_rls_rule", pk)

    def import_assets(self, resource: str, *, file_path: Path, passwords: dict | None = None, overwrite: bool = False) -> dict:
        return self._record("import_assets", resource, file_path=str(file_path), passwords=passwords, overwrite=overwrite)

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "FakeSupersetClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
