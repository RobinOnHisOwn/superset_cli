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
    help="Superset CLI for self-hosted instances. Read commands are unrestricted; every write command requires --allow-write per invocation.",
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
sqllab_app = typer.Typer(help="SQL Lab execute, estimate, format, and stop. Write commands require --allow-write.")
security_app = typer.Typer(help="Security/admin write commands (roles, users, RLS). All require --allow-write.")
rls_app = typer.Typer(help="Row-level security rule writes. Require --allow-write.")
import_app = typer.Typer(help="Server-side asset imports via multipart upload. Require --allow-write.")
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
app.add_typer(sqllab_app, name="sqllab")
app.add_typer(security_app, name="security")
security_app.add_typer(rls_app, name="rls")
app.add_typer(import_app, name="import")


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


# ----- write-command infrastructure (ADR 0009, 0010) -----

_ALLOW_WRITE_HELP = (
    "Required to actually perform the write. Without it the command is a dry-run."
)
_ALLOW_WRITE_OPT = typer.Option("--allow-write", help=_ALLOW_WRITE_HELP)
_BODY_OPT = typer.Option("--body", help="JSON request body. Use '-' to read from stdin.")
_FILE_OPT = typer.Option("--file", help="Path to a JSON or ZIP file for the request payload.")


def _require_allow_write(allow_write: bool, *, action: str) -> None:
    if allow_write:
        return
    typer.echo(
        f"This would {action}. Re-run with --allow-write to perform the write."
    )
    raise typer.Exit(code=1)


def _load_body(body: str | None, file: Path | None) -> dict:
    if body is None and file is None:
        return {}
    if body is not None and file is not None:
        typer.echo("Pass either --body or --file, not both.")
        raise typer.Exit(code=2)
    if body is not None:
        if body == "-":
            import sys
            body = sys.stdin.read()
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            typer.echo(f"Invalid JSON for --body: {exc}")
            raise typer.Exit(code=2)
    try:
        return json.loads(file.read_text())
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in --file: {exc}")
        raise typer.Exit(code=2)


def _run_write(
    *,
    instance_name: str,
    state_dir: Path,
    ctx: typer.Context,
    call,
    as_json: bool,
    human_line: str,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path) as client:
            payload = call(client)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    typer.echo(human_line)


@app.command("api")
def api_request(
    ctx: typer.Context,
    instance_name: str,
    path: str,
    method: Annotated[str, typer.Option("--method", "-X", help="GET, POST, PUT, PATCH, or DELETE.")] = "GET",
    param: Annotated[list[str] | None, typer.Option("--param", help="Query KEY=VALUE; repeat as needed.")] = None,
    body: Annotated[str | None, typer.Option("--body", help="JSON object, or - for stdin.")] = None,
    file: Annotated[Path | None, typer.Option("--file", help="JSON body file.")] = None,
    allow_write: Annotated[bool, typer.Option("--allow-write", help="Required to actually perform the write. Without it the command is a dry-run.")] = False,
    state_dir: Annotated[Path, typer.Option("--state-dir")] = DEFAULT_STATE_DIR,
    browser: Annotated[str, typer.Option("--browser", callback=_validate_browser, help=_BROWSER_HELP)] = DEFAULT_BROWSER,
    as_json: Annotated[bool, typer.Option("--json", help="Compact full JSON response.")] = False,
) -> None:
    """Call a custom API endpoint; automatically import browser cookies once if needed."""
    method = method.upper()
    try:
        SupersetClient.validate_api_path(path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise typer.BadParameter("Unsupported --method; use GET, POST, PUT, PATCH, or DELETE.")
    params = []
    for item in param or []:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise typer.BadParameter("--param requires KEY=VALUE.")
        params.append((key, value))
    if method != "GET":
        _require_allow_write(allow_write, action=f"send {method} {path} on instance '{instance_name}'")
    if method == "GET" and (body is not None or file is not None):
        raise typer.BadParameter("GET does not accept --body or --file.")
    try:
        payload_body = _load_body(body, file) if body is not None or file is not None else None
    except OSError as exc:
        raise typer.BadParameter(f"Cannot read --file: {exc}") from exc
    if (body is not None or file is not None) and not isinstance(payload_body, dict):
        raise typer.BadParameter("The request body must be a JSON object.")
    instance = _require_instance(ctx, instance_name)
    storage_path = get_storage_state_path(state_dir=state_dir, instance_name=instance_name)

    def validate(candidate: Path) -> bool:
        with SupersetClient(base_url=instance.base_url, storage_state_path=candidate) as client:
            try:
                client.request("GET", "/api/v1/me/")
                return True
            except AuthExpiredError:
                return False

    with _api_errors():
        if not storage_path.exists() or not validate(storage_path):
            typer.echo(f"Importing browser cookies for '{instance_name}'...", err=True)
            try:
                import_browser_cookies(base_url=instance.base_url, storage_state_path=storage_path,
                                      browser=browser, validate=validate)
            except NoCookiesFoundError as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(code=1) from exc
        with SupersetClient(base_url=instance.base_url, storage_state_path=storage_path) as client:
            payload = client.request(method, path, params=params, json_body=payload_body)
    typer.echo(json.dumps(payload, separators=(",", ":") if as_json else None, indent=None if as_json else 2))


# ----- charts -----

@charts_app.command("create")
def charts_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a chart on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_chart(payload_body),
        human_line="Created chart.",
    )


@charts_app.command("update")
def charts_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update chart {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_chart(pk, payload_body),
        human_line=f"Updated chart {pk}.",
    )


@charts_app.command("delete")
def charts_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete chart {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_chart(pk),
        human_line=f"Deleted chart {pk}.",
    )


@charts_app.command("favorite")
def charts_favorite(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"favorite chart {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.favorite_chart(pk),
        human_line=f"Favorited chart {pk}.",
    )


@charts_app.command("unfavorite")
def charts_unfavorite(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"unfavorite chart {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.unfavorite_chart(pk),
        human_line=f"Unfavorited chart {pk}.",
    )


# ----- dashboards -----

@dashboards_app.command("create")
def dashboards_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a dashboard on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_dashboard(payload_body),
        human_line="Created dashboard.",
    )


@dashboards_app.command("update")
def dashboards_update(
    ctx: typer.Context, instance_name: str, id_or_slug: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update dashboard {id_or_slug} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_dashboard(id_or_slug, payload_body),
        human_line=f"Updated dashboard {id_or_slug}.",
    )


@dashboards_app.command("delete")
def dashboards_delete(
    ctx: typer.Context, instance_name: str, id_or_slug: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete dashboard {id_or_slug} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_dashboard(id_or_slug),
        human_line=f"Deleted dashboard {id_or_slug}.",
    )


@dashboards_app.command("favorite")
def dashboards_favorite(
    ctx: typer.Context, instance_name: str, id_or_slug: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"favorite dashboard {id_or_slug} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.favorite_dashboard(id_or_slug),
        human_line=f"Favorited dashboard {id_or_slug}.",
    )


@dashboards_app.command("unfavorite")
def dashboards_unfavorite(
    ctx: typer.Context, instance_name: str, id_or_slug: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"unfavorite dashboard {id_or_slug} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.unfavorite_dashboard(id_or_slug),
        human_line=f"Unfavorited dashboard {id_or_slug}.",
    )


@dashboards_app.command("copy")
def dashboards_copy(
    ctx: typer.Context, instance_name: str, id_or_slug: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"copy dashboard {id_or_slug} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.copy_dashboard(id_or_slug, payload_body),
        human_line=f"Copied dashboard {id_or_slug}.",
    )


# ----- datasets -----

@datasets_app.command("create")
def datasets_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a dataset on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_dataset(payload_body),
        human_line="Created dataset.",
    )


@datasets_app.command("update")
def datasets_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update dataset {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_dataset(pk, payload_body),
        human_line=f"Updated dataset {pk}.",
    )


@datasets_app.command("delete")
def datasets_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete dataset {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_dataset(pk),
        human_line=f"Deleted dataset {pk}.",
    )


@datasets_app.command("refresh")
def datasets_refresh(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"refresh dataset {pk} columns on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.refresh_dataset(pk),
        human_line=f"Refreshed dataset {pk}.",
    )


# ----- databases -----

@databases_app.command("create")
def databases_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a database on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_database(payload_body),
        human_line="Created database.",
    )


@databases_app.command("update")
def databases_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update database {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_database(pk, payload_body),
        human_line=f"Updated database {pk}.",
    )


@databases_app.command("delete")
def databases_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete database {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_database(pk),
        human_line=f"Deleted database {pk}.",
    )


@databases_app.command("test-connection")
def databases_test_connection(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"send a database test-connection request to instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.test_database_connection(payload_body),
        human_line="Test connection sent.",
    )


# ----- saved queries -----

@saved_queries_app.command("create")
def saved_queries_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a saved query on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_saved_query(payload_body),
        human_line="Created saved query.",
    )


@saved_queries_app.command("update")
def saved_queries_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update saved query {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_saved_query(pk, payload_body),
        human_line=f"Updated saved query {pk}.",
    )


@saved_queries_app.command("delete")
def saved_queries_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete saved query {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_saved_query(pk),
        human_line=f"Deleted saved query {pk}.",
    )


# ----- sqllab -----

@sqllab_app.command("execute")
def sqllab_execute(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"execute SQL via SQL Lab on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.execute_sql(payload_body),
        human_line="SQL executed.",
    )


@sqllab_app.command("format-sql")
def sqllab_format_sql(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"format SQL via SQL Lab on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.format_sql(payload_body),
        human_line="SQL formatted.",
    )


@sqllab_app.command("estimate")
def sqllab_estimate(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"estimate SQL cost via SQL Lab on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.estimate_sql(payload_body),
        human_line="SQL estimate requested.",
    )


@sqllab_app.command("stop-query")
def sqllab_stop_query(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"stop a SQL Lab query on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.stop_sql_query(payload_body),
        human_line="Stop request sent.",
    )


# ----- tags -----

@tags_app.command("create")
def tags_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a tag on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_tag(payload_body),
        human_line="Created tag.",
    )


@tags_app.command("update")
def tags_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update tag {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_tag(pk, payload_body),
        human_line=f"Updated tag {pk}.",
    )


@tags_app.command("delete")
def tags_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete tag {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_tag(pk),
        human_line=f"Deleted tag {pk}.",
    )


# ----- themes -----

@themes_app.command("create")
def themes_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a theme on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_theme(payload_body),
        human_line="Created theme.",
    )


@themes_app.command("update")
def themes_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update theme {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_theme(pk, payload_body),
        human_line=f"Updated theme {pk}.",
    )


@themes_app.command("delete")
def themes_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete theme {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_theme(pk),
        human_line=f"Deleted theme {pk}.",
    )


# ----- security: roles -----

@security_app.command("role-create")
def security_role_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a security role on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_role(payload_body),
        human_line="Created role.",
    )


@security_app.command("role-update")
def security_role_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update security role {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_role(pk, payload_body),
        human_line=f"Updated role {pk}.",
    )


@security_app.command("role-delete")
def security_role_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete security role {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_role(pk),
        human_line=f"Deleted role {pk}.",
    )


# ----- security: users -----

@security_app.command("user-create")
def security_user_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a security user on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_user(payload_body),
        human_line="Created user.",
    )


@security_app.command("user-update")
def security_user_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update security user {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_user(pk, payload_body),
        human_line=f"Updated user {pk}.",
    )


@security_app.command("user-delete")
def security_user_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete security user {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_user(pk),
        human_line=f"Deleted user {pk}.",
    )


# ----- security: rls -----

@rls_app.command("create")
def security_rls_create(
    ctx: typer.Context, instance_name: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"create a row-level security rule on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.create_rls_rule(payload_body),
        human_line="Created RLS rule.",
    )


@rls_app.command("update")
def security_rls_update(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    payload_body = _load_body(body, file)
    _require_allow_write(allow_write, action=f"update row-level security rule {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.update_rls_rule(pk, payload_body),
        human_line=f"Updated RLS rule {pk}.",
    )


@rls_app.command("delete")
def security_rls_delete(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"delete row-level security rule {pk} on instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.delete_rls_rule(pk),
        human_line=f"Deleted RLS rule {pk}.",
    )


# ----- asset import -----

_IMPORT_RESOURCES = {"dashboard", "chart", "dataset", "database", "saved_query"}


@import_app.command("upload")
def import_upload(
    ctx: typer.Context,
    instance_name: str,
    resource: str,
    file: Annotated[Path, typer.Option("--file", help="Path to the import ZIP bundle.")],
    passwords: Annotated[str | None, typer.Option("--passwords", help="JSON object mapping file paths to passwords.")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite existing assets with matching identifiers.")] = False,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    if resource not in _IMPORT_RESOURCES:
        typer.echo(
            f"Unsupported import resource '{resource}'. Use one of: {', '.join(sorted(_IMPORT_RESOURCES))}."
        )
        raise typer.Exit(code=2)
    if not file.exists():
        typer.echo(f"Import file not found: {file}")
        raise typer.Exit(code=2)
    passwords_payload: dict | None = None
    if passwords is not None:
        try:
            passwords_payload = json.loads(passwords)
        except json.JSONDecodeError as exc:
            typer.echo(f"Invalid JSON for --passwords: {exc}")
            raise typer.Exit(code=2)
    _require_allow_write(allow_write, action=f"import {resource} bundle '{file.name}' to instance '{instance_name}'")
    _run_write(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        call=lambda c: c.import_assets(
            resource, file_path=file, passwords=passwords_payload, overwrite=overwrite,
        ),
        human_line=f"Imported {resource} bundle from {file.name}.",
    )
