import json
from pathlib import Path

import httpx
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import NotFoundError
from fakes import FakeSupersetClient

runner = CliRunner()


def test_databases_get_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "ghost", "31", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_databases_get_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"],
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_databases_get_returns_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(state_dir), "--json"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(
        {"id": 31, "database_name": "analytics", "backend": "snowflake"},
        separators=(",", ":"),
    )


def test_databases_get_returns_human_readable(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "ID: 31" in result.stdout
    assert "Name: analytics" in result.stdout
    assert "Backend: snowflake" in result.stdout


def test_databases_get_not_found_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NotFoundFake(FakeSupersetClient):
        def get_database(self, pk: str) -> dict:
            raise NotFoundError("Resource not found: /api/v1/database/99")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NotFoundFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "99", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Resource not found" in result.stdout


def test_databases_get_network_error_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NetworkErrorFake(FakeSupersetClient):
        def get_database(self, pk: str) -> dict:
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NetworkErrorFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Network error" in result.stdout


def test_databases_get_closes_client(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[FakeSupersetClient] = []

    class CapturingFake(FakeSupersetClient):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingFake)

    runner.invoke(
        app,
        ["--config", str(config_path), "databases", "get", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert captured[0].closed


def test_databases_schemas_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "schemas", "ghost", "31", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_databases_schemas_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"],
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "schemas", "prod", "31", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_databases_schemas_returns_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "schemas", "prod", "31", "--state-dir", str(state_dir), "--json"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(["analytics", "public"], separators=(",", ":"))


def test_databases_schemas_returns_human_readable(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "schemas", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "analytics" in result.stdout
    assert "public" in result.stdout


def test_databases_schemas_forwards_params(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[dict] = []

    class CapturingSchemasFake(FakeSupersetClient):
        def get_database_schemas(self, pk: str, *, catalog: str | None = None, force: bool = False) -> list[str]:
            captured.append({"pk": pk, "catalog": catalog, "force": force})
            return super().get_database_schemas(pk, catalog=catalog, force=force)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingSchemasFake)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "schemas", "prod", "31",
            "--state-dir", str(state_dir), "--catalog", "main", "--force",
        ],
    )

    assert result.exit_code == 0
    assert captured[0] == {"pk": "31", "catalog": "main", "force": True}


def test_databases_schemas_not_found_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NotFoundSchemasFake(FakeSupersetClient):
        def get_database_schemas(self, pk: str, *, catalog: str | None = None, force: bool = False) -> list[str]:
            raise NotFoundError("Resource not found: /api/v1/database/99/schemas/")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NotFoundSchemasFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "schemas", "prod", "99", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Resource not found" in result.stdout


def test_databases_schemas_network_error_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NetworkErrorSchemasFake(FakeSupersetClient):
        def get_database_schemas(self, pk: str, *, catalog: str | None = None, force: bool = False) -> list[str]:
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NetworkErrorSchemasFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "schemas", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "Network error" in result.stdout


def test_databases_schemas_empty_returns_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class EmptySchemasFake(FakeSupersetClient):
        def get_database_schemas(self, pk: str, *, catalog: str | None = None, force: bool = False) -> list[str]:
            return []

    monkeypatch.setattr("superset_cli.cli.SupersetClient", EmptySchemasFake)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "schemas", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 0
    assert "No schemas found." in result.stdout


def test_databases_schemas_closes_client(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[FakeSupersetClient] = []

    class CapturingSchemasCloseFake(FakeSupersetClient):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingSchemasCloseFake)

    runner.invoke(
        app,
        ["--config", str(config_path), "databases", "schemas", "prod", "31", "--state-dir", str(state_dir)],
    )

    assert captured[0].closed


def test_databases_tables_unknown_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "tables", "ghost", "31", "--schema", "analytics", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "Unknown instance 'ghost'" in result.stdout


def test_databases_tables_requires_saved_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "prod", "https://superset.example.com"],
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "databases", "tables", "prod", "31", "--schema", "analytics", "--state-dir", str(tmp_path / "state")],
    )

    assert result.exit_code == 1
    assert "No saved auth state for instance 'prod'" in result.stdout


def test_databases_tables_returns_json(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "tables", "prod", "31",
            "--schema", "analytics", "--state-dir", str(state_dir), "--json",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(
        {
            "count": 2,
            "result": [
                {"value": "orders", "type": "table", "extra": {}},
                {"value": "customer_view", "type": "view", "extra": {}},
            ],
        },
        separators=(",", ":"),
    )


def test_databases_tables_returns_human_readable(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient", FakeSupersetClient)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "tables", "prod", "31",
            "--schema", "analytics", "--state-dir", str(state_dir),
        ],
    )

    assert result.exit_code == 0
    assert "orders (type=table)" in result.stdout
    assert "customer_view (type=view)" in result.stdout


def test_databases_tables_forwards_params(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[dict] = []

    class CapturingTablesFake(FakeSupersetClient):
        def get_database_tables(
            self,
            pk: str,
            *,
            schema_name: str,
            catalog_name: str | None = None,
            force: bool = False,
        ) -> dict:
            captured.append(
                {
                    "pk": pk,
                    "schema_name": schema_name,
                    "catalog_name": catalog_name,
                    "force": force,
                }
            )
            return super().get_database_tables(
                pk,
                schema_name=schema_name,
                catalog_name=catalog_name,
                force=force,
            )

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingTablesFake)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "tables", "prod", "31",
            "--schema", "analytics", "--catalog", "main", "--force", "--state-dir", str(state_dir),
        ],
    )

    assert result.exit_code == 0
    assert captured[0] == {
        "pk": "31",
        "schema_name": "analytics",
        "catalog_name": "main",
        "force": True,
    }


def test_databases_tables_not_found_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NotFoundTablesFake(FakeSupersetClient):
        def get_database_tables(
            self,
            pk: str,
            *,
            schema_name: str,
            catalog_name: str | None = None,
            force: bool = False,
        ) -> dict:
            raise NotFoundError("Resource not found: /api/v1/database/99/tables/")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NotFoundTablesFake)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "tables", "prod", "99",
            "--schema", "analytics", "--state-dir", str(state_dir),
        ],
    )

    assert result.exit_code == 1
    assert "Resource not found" in result.stdout


def test_databases_tables_network_error_prints_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class NetworkErrorTablesFake(FakeSupersetClient):
        def get_database_tables(
            self,
            pk: str,
            *,
            schema_name: str,
            catalog_name: str | None = None,
            force: bool = False,
        ) -> dict:
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NetworkErrorTablesFake)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "tables", "prod", "31",
            "--schema", "analytics", "--state-dir", str(state_dir),
        ],
    )

    assert result.exit_code == 1
    assert "Network error" in result.stdout


def test_databases_tables_empty_returns_message(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup

    class EmptyTablesFake(FakeSupersetClient):
        def get_database_tables(
            self,
            pk: str,
            *,
            schema_name: str,
            catalog_name: str | None = None,
            force: bool = False,
        ) -> dict:
            return {"count": 0, "result": []}

    monkeypatch.setattr("superset_cli.cli.SupersetClient", EmptyTablesFake)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "tables", "prod", "31",
            "--schema", "analytics", "--state-dir", str(state_dir),
        ],
    )

    assert result.exit_code == 0
    assert "No tables found." in result.stdout


def test_databases_tables_closes_client(monkeypatch, instance_setup) -> None:
    config_path, state_dir = instance_setup
    captured: list[FakeSupersetClient] = []

    class CapturingTablesCloseFake(FakeSupersetClient):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            captured.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CapturingTablesCloseFake)

    runner.invoke(
        app,
        [
            "--config", str(config_path), "databases", "tables", "prod", "31",
            "--schema", "analytics", "--state-dir", str(state_dir),
        ],
    )

    assert captured[0].closed
