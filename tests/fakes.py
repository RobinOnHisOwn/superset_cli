from pathlib import Path


class FakeSupersetClient:
    def __init__(self, *, base_url: str, storage_state_path: Path) -> None:
        self.base_url = base_url
        self.storage_state_path = storage_state_path
        self.closed = False

    def get_current_user(self) -> dict:
        return {
            "id": 3,
            "username": "agent@example.com",
            "first_name": "Superset",
            "last_name": "Agent",
        }

    def list_dashboards(self, *, page: int | None = None, page_size: int | None = None) -> dict:
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

    def list_charts(self, *, page: int | None = None, page_size: int | None = None) -> dict:
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

    def list_datasets(self, *, page: int | None = None, page_size: int | None = None) -> dict:
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

    def list_databases(self, *, page: int | None = None, page_size: int | None = None) -> dict:
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

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "FakeSupersetClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
