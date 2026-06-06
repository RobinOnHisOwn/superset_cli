import json
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Generator

import httpx
import typer

from superset_cli.auth import DEFAULT_BROWSER, SUPPORTED_BROWSERS, NoCookiesFoundError, format_expiry, get_auth_status, get_instance_dir, get_storage_state_path, import_browser_cookies, remove_auth_state
from superset_cli.client import AuthExpiredError, NotFoundError, SupersetClient
from superset_cli.config import DEFAULT_STATE_DIR, get_instance, load_config, remove_instance, save_config, upsert_instance
from superset_cli.models import InstanceConfig

app = typer.Typer(
    help="Superset CLI for self-hosted instances. Read-only bootstrap commands.",
    no_args_is_help=True,
)
instances_app = typer.Typer(help="Inspect configured Superset instances.")
auth_app = typer.Typer(help="Authenticate against a configured Superset instance.")
openapi_app = typer.Typer(help="Fetch the live Superset OpenAPI specification.")
me_app = typer.Typer(help="Read current-user metadata from a configured Superset instance.")
dashboards_app = typer.Typer(help="Read dashboards from a configured Superset instance.")
charts_app = typer.Typer(help="Read charts from a configured Superset instance.")
datasets_app = typer.Typer(help="Read datasets from a configured Superset instance.")
databases_app = typer.Typer(help="Read databases from a configured Superset instance.")
permalinks_app = typer.Typer(help="Resolve Superset permalinks (dashboard, explore, sqllab).")
datasources_app = typer.Typer(help="Read datasource (table/native) details from a configured Superset instance.")
annotation_layers_app = typer.Typer(help="Read annotation layers from a configured Superset instance.")
css_templates_app = typer.Typer(help="Read CSS templates from a configured Superset instance.")
themes_app = typer.Typer(help="Read themes from a configured Superset instance.")
tags_app = typer.Typer(help="Read tags from a configured Superset instance.")
reports_app = typer.Typer(help="Read report schedules from a configured Superset instance.")
saved_queries_app = typer.Typer(help="Read saved SQL queries from a configured Superset instance.")
queries_app = typer.Typer(help="Read SQL Lab query history from a configured Superset instance.")
logs_app = typer.Typer(help="Read action logs and recent activity from a configured Superset instance.")
app.add_typer(instances_app, name="instances")
app.add_typer(auth_app, name="auth")
app.add_typer(openapi_app, name="openapi")
app.add_typer(me_app, name="me")
app.add_typer(dashboards_app, name="dashboards")
app.add_typer(charts_app, name="charts")
app.add_typer(datasets_app, name="datasets")
app.add_typer(databases_app, name="databases")
app.add_typer(permalinks_app, name="permalinks")
app.add_typer(datasources_app, name="datasources")
app.add_typer(annotation_layers_app, name="annotation-layers")
app.add_typer(css_templates_app, name="css-templates")
app.add_typer(themes_app, name="themes")
app.add_typer(tags_app, name="tags")
app.add_typer(reports_app, name="reports")
app.add_typer(saved_queries_app, name="saved-queries")
app.add_typer(queries_app, name="queries")
app.add_typer(logs_app, name="logs")


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
    except httpx.HTTPStatusError as exc:
        typer.echo(f"Superset API error: HTTP {exc.response.status_code}")
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


def _validate_browser(value: str) -> str:
    if value not in SUPPORTED_BROWSERS:
        raise typer.BadParameter(
            f"Unsupported browser '{value}'. Choose one of: {', '.join(SUPPORTED_BROWSERS)}."
        )
    return value


_BROWSER_HELP = (
    "Browser to read cookies from. Default 'auto' tries chrome, edge, brave, firefox, zen, safari "
    "in order and picks the first with a session cookie for the target host. "
    "You must already be signed in to Superset in that browser."
)


@auth_app.command("login")
def auth_login(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    browser: Annotated[
        str,
        typer.Option("--browser", help=_BROWSER_HELP, callback=_validate_browser),
    ] = DEFAULT_BROWSER,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = get_storage_state_path(state_dir=state_dir, instance_name=instance_name)
    try:
        summary = import_browser_cookies(
            base_url=instance.base_url,
            storage_state_path=storage_state_path,
            browser=browser,
        )
    except NoCookiesFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    payload = {
        "instance": instance.name,
        "base_url": instance.base_url,
        "browser_used": summary["browser_used"],
        "cookie_count": summary["cookie_count"],
        "storage_state_path": str(storage_state_path),
    }
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    plural = "" if summary["cookie_count"] == 1 else "s"
    typer.echo(
        f"Imported {summary['cookie_count']} cookie{plural} from {summary['browser_used']}."
    )
    typer.echo(f"Saved storage state to {storage_state_path}")


@auth_app.command("logout")
def auth_logout(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
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
        typer.Option("--state-dir", help="Directory for saved auth state."),
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
    typer.echo(f"Earliest cookie expiry: {format_expiry(payload['earliest_cookie_expiry'])}")
    typer.echo(f"Expired: {payload['expired']}")


@auth_app.command("validate")
def auth_validate(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
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


@openapi_app.command("fetch")
def openapi_fetch(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_openapi_spec()

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    info = payload.get("info") or {}
    typer.echo(f"OpenAPI: {payload.get('openapi')}")
    typer.echo(f"Title: {info.get('title')}")
    typer.echo(f"Version: {info.get('version')}")


@me_app.command("show")
def me_show(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            user = client.get_current_user()

    if as_json:
        typer.echo(json.dumps(user, separators=(",", ":")))
        return

    typer.echo(f"User: {user.get('username')}")
    name = " ".join(part for part in [user.get("first_name"), user.get("last_name")] if part)
    typer.echo(f"Name: {name}")


@me_app.command("roles")
def me_roles(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_current_user_roles()

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    roles = payload.get("roles") or []
    if not roles:
        typer.echo("No roles assigned.")
        return
    for role in roles:
        typer.echo(role.get("name") if isinstance(role, dict) else str(role))


@dashboards_app.command("list")
def dashboards_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", help="Number of results per page.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by dashboard title using Superset contains matching.")] = None,
    order_column: Annotated[str | None, typer.Option("--order-column", help="Superset list field to order by.")] = None,
    order_direction: Annotated[str | None, typer.Option("--order-direction", help="Sort direction: asc or desc.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.list_dashboards(
                page=page,
                page_size=page_size,
                search=search,
                order_column=order_column,
                order_direction=order_direction,
            )

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
        typer.Option("--state-dir", help="Directory for saved auth state."),
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


@dashboards_app.command("charts")
def dashboards_charts(
    ctx: typer.Context,
    instance_name: str,
    id_or_slug: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_dashboard_charts(id_or_slug)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if not payload:
        typer.echo("No charts found.")
        return

    for chart in payload:
        typer.echo(
            f"{chart.get('id')}: {chart.get('slice_name')} "
            f"(viz_type={chart.get('viz_type')})"
        )


@dashboards_app.command("datasets")
def dashboards_datasets(
    ctx: typer.Context,
    instance_name: str,
    id_or_slug: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_dashboard_datasets(id_or_slug)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if not payload:
        typer.echo("No datasets found.")
        return

    for dataset in payload:
        typer.echo(
            f"{dataset.get('id')}: {dataset.get('table_name')} "
            f"(schema={dataset.get('schema')})"
        )


@charts_app.command("list")
def charts_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", help="Number of results per page.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by chart name using Superset contains matching.")] = None,
    order_column: Annotated[str | None, typer.Option("--order-column", help="Superset list field to order by.")] = None,
    order_direction: Annotated[str | None, typer.Option("--order-direction", help="Sort direction: asc or desc.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.list_charts(
                page=page,
                page_size=page_size,
                search=search,
                order_column=order_column,
                order_direction=order_direction,
            )

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
        typer.Option("--state-dir", help="Directory for saved auth state."),
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
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", help="Number of results per page.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by dataset table name using Superset contains matching.")] = None,
    order_column: Annotated[str | None, typer.Option("--order-column", help="Superset list field to order by.")] = None,
    order_direction: Annotated[str | None, typer.Option("--order-direction", help="Sort direction: asc or desc.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.list_datasets(
                page=page,
                page_size=page_size,
                search=search,
                order_column=order_column,
                order_direction=order_direction,
            )

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
        typer.Option("--state-dir", help="Directory for saved auth state."),
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
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", help="Number of results per page.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by database name using Superset contains matching.")] = None,
    order_column: Annotated[str | None, typer.Option("--order-column", help="Superset list field to order by.")] = None,
    order_direction: Annotated[str | None, typer.Option("--order-direction", help="Sort direction: asc or desc.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.list_databases(
                page=page,
                page_size=page_size,
                search=search,
                order_column=order_column,
                order_direction=order_direction,
            )

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
        typer.Option("--state-dir", help="Directory for saved auth state."),
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


@databases_app.command("schemas")
def databases_schemas(
    ctx: typer.Context,
    instance_name: str,
    pk: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    catalog: Annotated[str | None, typer.Option("--catalog", help="Optional database catalog.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Bypass cached schema metadata.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_database_schemas(pk, catalog=catalog, force=force)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if not payload:
        typer.echo("No schemas found.")
        return

    for schema in payload:
        typer.echo(str(schema))


@databases_app.command("tables")
def databases_tables(
    ctx: typer.Context,
    instance_name: str,
    pk: str,
    schema_name: Annotated[str, typer.Option("--schema", help="Database schema to inspect.")],
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    catalog: Annotated[str | None, typer.Option("--catalog", help="Optional database catalog.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Bypass cached table metadata.")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_database_tables(pk, schema_name=schema_name, catalog_name=catalog, force=force)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    tables = payload.get("result", [])
    if not tables:
        typer.echo("No tables found.")
        return

    for table in tables:
        typer.echo(f"{table.get('value')} (type={table.get('type')})")


def _run_list(
    *,
    instance_name: str,
    state_dir: Path,
    ctx: typer.Context,
    list_call,
    as_json: bool,
    empty_message: str,
    line_formatter,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = list_call(client)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    items = payload.get("result", [])
    if not items:
        typer.echo(empty_message)
        return
    for item in items:
        typer.echo(line_formatter(item))


def _run_get(
    *,
    instance_name: str,
    state_dir: Path,
    ctx: typer.Context,
    get_call,
    as_json: bool,
    human_lines,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = get_call(client)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    for line in human_lines(payload):
        typer.echo(line)


_STATE_DIR_OPT = typer.Option("--state-dir", help="Directory for saved auth state.")
_JSON_OPT = typer.Option("--json", help="Return structured JSON output.")
_PAGE_OPT = typer.Option("--page", help="Page index (0-based).")
_PAGE_SIZE_OPT = typer.Option("--page-size", help="Number of results per page.")
_ORDER_COL_OPT = typer.Option("--order-column", help="Superset list field to order by.")
_ORDER_DIR_OPT = typer.Option("--order-direction", help="Sort direction: asc or desc.")


@annotation_layers_app.command("list")
def annotation_layers_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by annotation layer name.")] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        list_call=lambda c: c.list_annotation_layers(
            page=page, page_size=page_size, search=search,
            order_column=order_column, order_direction=order_direction,
        ),
        empty_message="No annotation layers found.",
        line_formatter=lambda x: f"{x.get('id')}: {x.get('name')}",
    )


@annotation_layers_app.command("get")
def annotation_layers_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_annotation_layer(pk),
        human_lines=lambda p: [
            f"ID: {p.get('id')}",
            f"Name: {p.get('name')}",
            f"Description: {p.get('descr')}",
        ],
    )


@css_templates_app.command("list")
def css_templates_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by CSS template name.")] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        list_call=lambda c: c.list_css_templates(
            page=page, page_size=page_size, search=search,
            order_column=order_column, order_direction=order_direction,
        ),
        empty_message="No CSS templates found.",
        line_formatter=lambda x: f"{x.get('id')}: {x.get('template_name')}",
    )


@css_templates_app.command("get")
def css_templates_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_css_template(pk),
        human_lines=lambda p: [
            f"ID: {p.get('id')}",
            f"Name: {p.get('template_name')}",
        ],
    )


@themes_app.command("list")
def themes_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by theme name.")] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        list_call=lambda c: c.list_themes(
            page=page, page_size=page_size, search=search,
            order_column=order_column, order_direction=order_direction,
        ),
        empty_message="No themes found.",
        line_formatter=lambda x: f"{x.get('id')}: {x.get('theme_name')}",
    )


@themes_app.command("get")
def themes_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_theme(pk),
        human_lines=lambda p: [
            f"ID: {p.get('id')}",
            f"Name: {p.get('theme_name')}",
        ],
    )


@tags_app.command("list")
def tags_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by tag name.")] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        list_call=lambda c: c.list_tags(
            page=page, page_size=page_size, search=search,
            order_column=order_column, order_direction=order_direction,
        ),
        empty_message="No tags found.",
        line_formatter=lambda x: f"{x.get('id')}: {x.get('name')} (type={x.get('type')})",
    )


@tags_app.command("get")
def tags_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_tag(pk),
        human_lines=lambda p: [
            f"ID: {p.get('id')}",
            f"Name: {p.get('name')}",
            f"Type: {p.get('type')}",
        ],
    )


@reports_app.command("list")
def reports_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by report name.")] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        list_call=lambda c: c.list_reports(
            page=page, page_size=page_size, search=search,
            order_column=order_column, order_direction=order_direction,
        ),
        empty_message="No reports found.",
        line_formatter=lambda x: f"{x.get('id')}: {x.get('name')} (type={x.get('type')}, active={x.get('active')})",
    )


@reports_app.command("get")
def reports_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_report(pk),
        human_lines=lambda p: [
            f"ID: {p.get('id')}",
            f"Name: {p.get('name')}",
            f"Type: {p.get('type')}",
            f"Active: {p.get('active')}",
        ],
    )


@saved_queries_app.command("list")
def saved_queries_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by saved query label.")] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        list_call=lambda c: c.list_saved_queries(
            page=page, page_size=page_size, search=search,
            order_column=order_column, order_direction=order_direction,
        ),
        empty_message="No saved queries found.",
        line_formatter=lambda x: f"{x.get('id')}: {x.get('label')} (schema={x.get('schema')})",
    )


@saved_queries_app.command("get")
def saved_queries_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_saved_query(pk),
        human_lines=lambda p: [
            f"ID: {p.get('id')}",
            f"Label: {p.get('label')}",
            f"Schema: {p.get('schema')}",
        ],
    )


@queries_app.command("list")
def queries_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by SQL contents.")] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        list_call=lambda c: c.list_queries(
            page=page, page_size=page_size, search=search,
            order_column=order_column, order_direction=order_direction,
        ),
        empty_message="No queries found.",
        line_formatter=lambda x: f"{x.get('id')}: status={x.get('status')} (rows={x.get('rows')})",
    )


@queries_app.command("get")
def queries_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_query(pk),
        human_lines=lambda p: [
            f"ID: {p.get('id')}",
            f"Status: {p.get('status')}",
            f"Rows: {p.get('rows')}",
        ],
    )


@logs_app.command("list")
def logs_list(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        list_call=lambda c: c.list_logs(
            page=page, page_size=page_size,
            order_column=order_column, order_direction=order_direction,
        ),
        empty_message="No logs found.",
        line_formatter=lambda x: f"{x.get('id')}: action={x.get('action')} dttm={x.get('dttm')}",
    )


@logs_app.command("get")
def logs_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_log(pk),
        human_lines=lambda p: [
            f"ID: {p.get('id')}",
            f"Action: {p.get('action')}",
            f"User: {p.get('user', {}).get('username') if isinstance(p.get('user'), dict) else p.get('user')}",
            f"When: {p.get('dttm')}",
        ],
    )


@logs_app.command("recent-activity")
def logs_recent_activity(
    ctx: typer.Context,
    instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_recent_activity()
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    items = payload.get("result", [])
    if not items:
        typer.echo("No recent activity.")
        return
    for item in items:
        typer.echo(f"{item.get('action')} on {item.get('item_title')} ({item.get('time')})")


@dashboards_app.command("embedded")
def dashboards_embedded(
    ctx: typer.Context, instance_name: str, id_or_slug: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        get_call=lambda c: c.get_dashboard_embedded(id_or_slug),
        human_lines=lambda p: [
            f"UUID: {p.get('uuid')}",
            f"Dashboard ID: {p.get('dashboard_id')}",
            f"Allowed domains: {', '.join(p.get('allowed_domains') or []) or '-'}",
        ],
    )


@datasets_app.command("related")
def datasets_related(
    ctx: typer.Context, instance_name: str, id_or_uuid: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_dataset_related_objects(id_or_uuid)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    charts = payload.get("charts", {})
    dashboards = payload.get("dashboards", {})
    typer.echo(f"Charts: {charts.get('count', 0)}")
    for ref in charts.get("result", []) or []:
        typer.echo(f"  - {ref.get('id')}: {ref.get('slice_name')}")
    typer.echo(f"Dashboards: {dashboards.get('count', 0)}")
    for ref in dashboards.get("result", []) or []:
        typer.echo(f"  - {ref.get('id')}: {ref.get('title')}")


@permalinks_app.command("resolve")
def permalinks_resolve(
    ctx: typer.Context,
    instance_name: str,
    kind: str,
    key: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    if kind not in {"dashboard", "explore", "sqllab"}:
        typer.echo(f"Unsupported permalink kind '{kind}'. Use 'dashboard', 'explore', or 'sqllab'.")
        raise typer.Exit(code=1)
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_permalink(kind, key)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    typer.echo(f"Kind: {kind}")
    typer.echo(f"Key: {key}")
    for field in ("state", "url", "dashboardId", "chartId"):
        if field in payload:
            typer.echo(f"{field}: {payload[field]}")


@datasources_app.command("column-values")
def datasources_column_values(
    ctx: typer.Context,
    instance_name: str,
    datasource_type: str,
    datasource_id: str,
    column: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_datasource_column_values(datasource_type, datasource_id, column)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    values = payload.get("result", [])
    if not values:
        typer.echo("No values returned.")
        return
    for value in values:
        typer.echo(str(value))


@charts_app.command("data")
def charts_data(
    ctx: typer.Context,
    instance_name: str,
    pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = client.get_chart_data(pk)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    queries = payload.get("result", [])
    typer.echo(f"Queries: {len(queries)}")
    for idx, query in enumerate(queries):
        rowcount = query.get("rowcount")
        if rowcount is None:
            data = query.get("data") or []
            rowcount = len(data)
        cols = query.get("colnames") or []
        typer.echo(f"  [{idx}] rows={rowcount} columns={','.join(cols)}")
