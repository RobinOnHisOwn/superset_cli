import json
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Generator

import httpx
import typer

from superset_agent_cli.auth import get_auth_status, get_instance_dir, get_profile_dir, get_storage_state_path, login_with_browser, remove_auth_state
from superset_agent_cli.client import AuthExpiredError, NotFoundError, SupersetClient
from superset_agent_cli.config import DEFAULT_STATE_DIR, get_instance, load_config, remove_instance, save_config, upsert_instance
from superset_agent_cli.models import InstanceConfig

app = typer.Typer(
    help="Superset agent CLI for self-hosted instances. Read-only bootstrap commands.",
    no_args_is_help=True,
)
instances_app = typer.Typer(help="Inspect configured Superset instances.")
auth_app = typer.Typer(help="Authenticate against a configured Superset instance.")
dashboards_app = typer.Typer(help="Read dashboards from a configured Superset instance.")
charts_app = typer.Typer(help="Read charts from a configured Superset instance.")
datasets_app = typer.Typer(help="Read datasets from a configured Superset instance.")
databases_app = typer.Typer(help="Read databases from a configured Superset instance.")
app.add_typer(instances_app, name="instances")
app.add_typer(auth_app, name="auth")
app.add_typer(dashboards_app, name="dashboards")
app.add_typer(charts_app, name="charts")
app.add_typer(datasets_app, name="datasets")
app.add_typer(databases_app, name="databases")


@app.callback()
def main(
    ctx: typer.Context,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Path to the CLI config file."),
    ] = None,
) -> None:
    ctx.obj = {"config_path": config_path}


def _get_config_path(ctx: typer.Context) -> Path | None:
    if ctx.obj is None:
        return None
    return ctx.obj.get("config_path")


def _require_instance(ctx: typer.Context, instance_name: str) -> InstanceConfig:
    config = load_config(_get_config_path(ctx))
    instance = get_instance(config, instance_name)
    if instance is None:
        typer.echo(f"Unknown instance '{instance_name}'. Add it with 'instances add' first.")
        raise typer.Exit(code=1)
    return instance


@contextmanager
def _api_errors() -> Generator[None, None, None]:
    try:
        yield
    except AuthExpiredError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    except NotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    except httpx.RequestError as exc:
        typer.echo(f"Network error: could not reach Superset ({exc})")
        raise typer.Exit(code=1)


def _require_storage_state(*, instance_name: str, state_dir: Path) -> Path:
    storage_state_path = get_storage_state_path(state_dir=state_dir, instance_name=instance_name)
    if not storage_state_path.exists():
        typer.echo(f"No saved auth state for instance '{instance_name}'. Run 'auth login' first.")
        raise typer.Exit(code=1)
    return storage_state_path


@instances_app.command("list")
def list_instances(
    ctx: typer.Context,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    config = load_config(_get_config_path(ctx))
    payload = {
        "instances": [
            {"name": instance.name, "base_url": instance.base_url}
            for instance in config.instances
        ]
    }
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if not payload["instances"]:
        typer.echo("No instances configured.")
        return

    for instance in payload["instances"]:
        typer.echo(f"{instance['name']}: {instance['base_url']}")


@instances_app.command("add")
def add_instance(
    ctx: typer.Context,
    name: str,
    base_url: str,
) -> None:
    config_path = _get_config_path(ctx)
    config = load_config(config_path)
    updated = upsert_instance(config, InstanceConfig(name=name, base_url=base_url))
    save_config(updated, config_path)
    typer.echo(f"Saved instance '{name}'.")


@instances_app.command("remove")
def remove_instance_cmd(
    ctx: typer.Context,
    name: str,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    config_path = _get_config_path(ctx)
    config = load_config(config_path)
    if get_instance(config, name) is None:
        typer.echo(f"Unknown instance '{name}'. Add it with 'instances add' first.")
        raise typer.Exit(code=1)
    updated = remove_instance(config, name)
    save_config(updated, config_path)
    if as_json:
        typer.echo(json.dumps({"removed": name}, separators=(",", ":")))
        return
    typer.echo(f"Removed instance '{name}'.")


@auth_app.command("login")
def auth_login(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    profile_dir = get_profile_dir(state_dir=state_dir, instance_name=instance_name)
    storage_state_path = get_storage_state_path(state_dir=state_dir, instance_name=instance_name)
    login_with_browser(
        base_url=instance.base_url,
        profile_dir=profile_dir,
        storage_state_path=storage_state_path,
    )
    payload = {
        "instance": instance.name,
        "base_url": instance.base_url,
        "profile_dir": str(profile_dir),
        "storage_state_path": str(storage_state_path),
    }
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"Saved browser profile to {profile_dir}")
    typer.echo(f"Saved storage state to {storage_state_path}")


@auth_app.command("logout")
def auth_logout(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    _require_instance(ctx, instance_name)
    instance_dir = get_instance_dir(state_dir=state_dir, instance_name=instance_name)
    if not instance_dir.exists():
        typer.echo(f"No saved auth state for instance '{instance_name}'. Nothing to remove.")
        raise typer.Exit(code=1)
    remove_auth_state(state_dir=state_dir, instance_name=instance_name)
    if as_json:
        typer.echo(json.dumps({"removed_auth_state": instance_name}, separators=(",", ":")))
        return
    typer.echo(f"Removed auth state for instance '{instance_name}'.")


@auth_app.command("status")
def auth_status(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    payload = {
        "instance": instance.name,
        "base_url": instance.base_url,
        **get_auth_status(storage_state_path=storage_state_path),
    }
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"Authenticated: {payload['authenticated']}")
    typer.echo(f"Saved storage state: {payload['storage_state_path']}")
    typer.echo(f"Cookie count: {payload['cookie_count']}")


@auth_app.command("validate")
def auth_validate(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            user = client.get_current_user()
    payload = {
        "instance": instance.name,
        "base_url": instance.base_url,
        "authenticated": True,
        "user": user,
    }
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"Authenticated: {payload['authenticated']}")
    typer.echo(f"User: {(user or {}).get('username')}")


@dashboards_app.command("list")
def dashboards_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", help="Number of results per page.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.list_dashboards(page=page, page_size=page_size)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    dashboards = payload.get("result", [])
    if not dashboards:
        typer.echo("No dashboards found.")
        return

    for dashboard in dashboards:
        typer.echo(
            f"{dashboard.get('id')}: {dashboard.get('dashboard_title')} "
            f"(published={dashboard.get('published')})"
        )


@dashboards_app.command("get")
def dashboards_get(
    ctx: typer.Context,
    instance_name: str,
    id_or_slug: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_dashboard(id_or_slug)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"ID: {payload.get('id')}")
    typer.echo(f"Title: {payload.get('dashboard_title')}")
    typer.echo(f"Slug: {payload.get('slug')}")
    typer.echo(f"Published: {payload.get('published')}")


@charts_app.command("list")
def charts_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", help="Number of results per page.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.list_charts(page=page, page_size=page_size)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    charts = payload.get("result", [])
    if not charts:
        typer.echo("No charts found.")
        return

    for chart in charts:
        typer.echo(
            f"{chart.get('id')}: {chart.get('slice_name')} "
            f"(viz_type={chart.get('viz_type')})"
        )


@charts_app.command("get")
def charts_get(
    ctx: typer.Context,
    instance_name: str,
    id_or_uuid: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_chart(id_or_uuid)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"ID: {payload.get('id')}")
    typer.echo(f"Name: {payload.get('slice_name')}")
    typer.echo(f"Viz type: {payload.get('viz_type')}")


@datasets_app.command("list")
def datasets_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", help="Number of results per page.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.list_datasets(page=page, page_size=page_size)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    datasets = payload.get("result", [])
    if not datasets:
        typer.echo("No datasets found.")
        return

    for dataset in datasets:
        typer.echo(
            f"{dataset.get('id')}: {dataset.get('table_name')} "
            f"(schema={dataset.get('schema')})"
        )


@datasets_app.command("get")
def datasets_get(
    ctx: typer.Context,
    instance_name: str,
    id_or_uuid: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_dataset(id_or_uuid)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"ID: {payload.get('id')}")
    typer.echo(f"Name: {payload.get('table_name')}")
    typer.echo(f"Schema: {payload.get('schema')}")


@databases_app.command("list")
def databases_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", help="Number of results per page.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.list_databases(page=page, page_size=page_size)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    databases = payload.get("result", [])
    if not databases:
        typer.echo("No databases found.")
        return

    for database in databases:
        typer.echo(
            f"{database.get('id')}: {database.get('database_name')} "
            f"(backend={database.get('backend')})"
        )


@databases_app.command("get")
def databases_get(
    ctx: typer.Context,
    instance_name: str,
    pk: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for browser profile and saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_database(pk)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"ID: {payload.get('id')}")
    typer.echo(f"Name: {payload.get('database_name')}")
    typer.echo(f"Backend: {payload.get('backend')}")
