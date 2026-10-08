import csv
import io
import os
from contextvars import ContextVar
import json
import math
import zipfile
from importlib.metadata import version as package_version
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Generator

import httpx
import typer

from superset_cli.auth import DEFAULT_BROWSER, SUPPORTED_BROWSERS, NoCookiesFoundError, export_playwright_state, format_expiry, get_auth_status, get_instance_dir, get_storage_state_path, import_browser_cookies, remove_auth_state
from superset_cli.client import HTTP_TIMEOUT, AuthExpiredError, NotFoundError, SupersetClient, format_api_error, parse_list_filters, validate_list_columns
from superset_cli.config import DEFAULT_STATE_DIR, get_instance, load_config, remove_instance, save_config, upsert_instance
from superset_cli.models import InstanceConfig, AuthConfig, JWTSettings, APIKeySettings
from superset_cli.api_key_auth import read_api_key
from superset_cli.jwt_auth import jwt_status, login_jwt, refresh_jwt
from superset_cli.instance_selection import InstanceTyper, resolve_instance_name

_ACTIVE_INSTANCE: ContextVar[InstanceConfig | None] = ContextVar("superset_instance", default=None)

app = InstanceTyper(
    help="Superset CLI for self-hosted instances. Read commands are unrestricted; every write command requires --allow-write per invocation.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
instances_app = InstanceTyper(help="Inspect configured Superset instances.")
auth_app = InstanceTyper(help="Authenticate against a configured Superset instance.")
openapi_app = InstanceTyper(help="Fetch the live Superset OpenAPI specification.")
me_app = InstanceTyper(help="Read current-user metadata from a configured Superset instance.")
dashboards_app = InstanceTyper(help="Read dashboards from a configured Superset instance.")
charts_app = InstanceTyper(help="Read charts from a configured Superset instance.")
datasets_app = InstanceTyper(help="Read datasets from a configured Superset instance.")
databases_app = InstanceTyper(help="Read databases from a configured Superset instance.")
permalinks_app = InstanceTyper(help="Resolve Superset permalinks (dashboard, explore, sqllab).")
datasources_app = InstanceTyper(help="Read datasource (table/native) details from a configured Superset instance.")
annotation_layers_app = InstanceTyper(help="Read annotation layers from a configured Superset instance.")
css_templates_app = InstanceTyper(help="Read CSS templates from a configured Superset instance.")
themes_app = InstanceTyper(help="Read themes from a configured Superset instance.")
tags_app = InstanceTyper(help="Read tags from a configured Superset instance.")
reports_app = InstanceTyper(help="Read report schedules from a configured Superset instance.")
saved_queries_app = InstanceTyper(help="Read saved SQL queries from a configured Superset instance.")
queries_app = InstanceTyper(help="Read SQL Lab query history from a configured Superset instance.")
logs_app = InstanceTyper(help="Read action logs and recent activity from a configured Superset instance.")
sqllab_app = InstanceTyper(help="SQL Lab execute, estimate, format, and stop. Write commands require --allow-write.")
security_app = InstanceTyper(help="Security/admin write commands (roles, users, RLS). All require --allow-write.")
rls_app = InstanceTyper(help="Row-level security rule writes. Require --allow-write.")
import_app = InstanceTyper(help="Server-side asset imports via multipart upload. Require --allow-write.")
app.add_typer(instances_app, name="instances")
app.add_typer(auth_app, name="auth")
jwt_app = InstanceTyper(help="Direct JWT login for DB/LDAP deployments; environment-only credentials.")
auth_app.add_typer(jwt_app, name="jwt")
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
roles_app = InstanceTyper(help="Read security roles.")
users_app = InstanceTyper(help="Read security users (server permissions apply).")
explore_app = InstanceTyper(help="Read saved-chart Explore state.")
security_app.add_typer(roles_app, name="roles")
security_app.add_typer(users_app, name="users")
app.add_typer(explore_app, name="explore")
app.add_typer(import_app, name="import")
cache_app = InstanceTyper(help="Targeted cache administration. Requires --allow-write.")
app.add_typer(cache_app, name="cache")


def _validate_list_filters(value):
    try:
        return parse_list_filters(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _validate_list_columns(value):
    try:
        return validate_list_columns(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _validate_list_page(ctx: typer.Context, value):
    if value is not None and ctx.params.get("all_pages"):
        raise typer.BadParameter("--all cannot be combined with --page.")
    return value


def _validate_list_all(ctx: typer.Context, value):
    if value and ctx.params.get("page") is not None:
        raise typer.BadParameter("--all cannot be combined with --page.")
    return value


_LIST_FILTER_OPT = typer.Option("--filter", callback=_validate_list_filters, help='Repeat a JSON filter object with col, opr, and typed value. Not chart-data col=value syntax.')
_LIST_COLUMNS_OPT = typer.Option("--columns", callback=_validate_list_columns, help="Select a field on the server; repeat once per field.")
_LIST_ALL_OPT = typer.Option("--all", callback=_validate_list_all, help="Fetch every page, checking identities and counts. Not an atomic snapshot; incompatible with --page.")


def _list_options(filters, columns, all_pages, **query):
    options = {key: value for key, value in (("filters", filters), ("columns", columns), ("all_pages", all_pages)) if value}
    return {**options, **{key: value for key, value in query.items() if value is not None}}


def _print_list_projection(payload, columns, as_json):
    if not columns or as_json:
        return False
    for row in payload.get("result", []):
        typer.echo(json.dumps(row, separators=(",", ":")))
    return True


def _show_version(value: bool) -> bool:
    if value:
        typer.echo(f"superset-cli {package_version('superset-cli')}")
        raise typer.Exit()
    return value


@app.callback()
def main(
    ctx: typer.Context,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Path to the CLI config file."),
    ] = None,
    show_version: Annotated[bool, typer.Option("--version", callback=_show_version, is_eager=True, help="Show the running package version.")] = False,
    instance_override: Annotated[str | None, typer.Option("--instance", help="Instance when the subcommand omits its positional instance.")] = None,
    timeout: Annotated[float, typer.Option("--timeout", help="HTTP phase/inactivity timeout in seconds (not a total deadline). Must be finite and positive.")] = 30.0,
) -> None:
    if not math.isfinite(timeout) or timeout <= 0:
        raise typer.BadParameter("Must be a finite positive number of seconds.", param_hint="--timeout")
    timeout_token = HTTP_TIMEOUT.set(timeout)
    ctx.call_on_close(lambda: HTTP_TIMEOUT.reset(timeout_token))
    ctx.obj = {"config_path": config_path, "instance_override": instance_override}
    token = _ACTIVE_INSTANCE.set(None)
    ctx.call_on_close(lambda: _ACTIVE_INSTANCE.reset(token))


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
    _ACTIVE_INSTANCE.set(instance)
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
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    except httpx.HTTPStatusError as exc:
        typer.echo(format_api_error(exc), err=True)
        raise typer.Exit(code=1)
    except httpx.TimeoutException as exc:
        message = "HTTP request timed out."
        if exc.request.method not in {"GET", "HEAD", "OPTIONS"}:
            message += " Mutation outcome unknown; check server state before retrying."
        typer.echo(message, err=True)
        raise typer.Exit(code=1)
    except httpx.RequestError as exc:
        typer.echo(f"Network error: could not reach Superset ({exc})")
        raise typer.Exit(code=1)


_DIFF_SKIP_FIELDS = {
    "id", "uuid", "slug", "url", "thumbnail_url", "changed_on", "changed_on_utc",
    "changed_on_delta_humanized", "created_on_delta_humanized", "changed_by",
    "changed_by_name", "created_by",
}


def diff_dashboard_records(a: dict, b: dict) -> list[tuple[str, str, str]]:
    """Compare two dashboard records, skipping identity/timestamp fields.

    Returns (field, a_value, b_value) for each differing field. Large values
    (position_json, json_metadata) are truncated so the output stays readable.
    """
    diffs: list[tuple[str, str, str]] = []
    for key in sorted(set(a) | set(b)):
        if key in _DIFF_SKIP_FIELDS:
            continue
        if a.get(key) != b.get(key):
            va = json.dumps(a.get(key), ensure_ascii=False)[:400]
            vb = json.dumps(b.get(key), ensure_ascii=False)[:400]
            diffs.append((key, va, vb))
    return diffs


def _client(*, instance: InstanceConfig, storage_state_path: Path | None):
    if instance.auth and instance.auth.mode == "api_key":
        if instance.auth.api_key is None:
            raise ValueError("API-key mode requires an environment binding; run 'auth api-key set'.")
        return SupersetClient(base_url=instance.base_url, api_key=instance.auth.api_key)
    return SupersetClient(base_url=instance.base_url, storage_state_path=storage_state_path)


def _require_storage_state(*, instance_name: str, state_dir: Path) -> Path | None:
    instance = _ACTIVE_INSTANCE.get()
    if instance is not None and instance.name == instance_name and instance.auth and instance.auth.mode == "api_key":
        return None
    jwt = instance is not None and instance.name == instance_name and instance.auth is not None and instance.auth.mode == "jwt"
    storage_state_path = (get_instance_dir(state_dir=state_dir, instance_name=instance_name) / "jwt-state.json"
                          if jwt else get_storage_state_path(state_dir=state_dir, instance_name=instance_name))
    if not storage_state_path.exists():
        command = "auth jwt login" if jwt else "auth login"
        typer.echo(f"No saved auth state for instance '{instance_name}'. Run '{command}' first.")
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
    if config.default_instance is not None:
        payload["default_instance"] = config.default_instance
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if config.default_instance is not None:
        typer.echo(f"Default instance: {config.default_instance}")
    if not payload["instances"]:
        typer.echo("No instances configured.")
        return

    for instance in payload["instances"]:
        typer.echo(f"{instance['name']}: {instance['base_url']}")


@instances_app.command("use")
def use_instance(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Argument()] = None,
    clear: Annotated[bool, typer.Option("--clear", help="Remove the persisted default.")] = False,
    show: Annotated[bool, typer.Option("--show", help="Show the currently resolved instance.")] = False,
) -> None:
    if (clear and name) or (show and (clear or name)):
        raise typer.BadParameter("Choose a name, --clear, or --show.")
    config = load_config(_get_config_path(ctx))
    if clear:
        save_config(config.model_copy(update={"default_instance": None}), _get_config_path(ctx))
        typer.echo("Cleared default instance.")
    elif name:
        if get_instance(config, name) is None:
            raise typer.BadParameter(f"Unknown instance '{name}'.")
        save_config(config.model_copy(update={"default_instance": name}), _get_config_path(ctx))
        typer.echo(f"Default instance: {name}")
    else:
        try:
            typer.echo(resolve_instance_name(config, override=(ctx.obj or {}).get("instance_override")))
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc


@instances_app.command("add")
def add_instance(
    ctx: typer.Context,
    name: str,
    base_url: str,
) -> None:
    config_path = _get_config_path(ctx)
    config = load_config(config_path)
    existing = get_instance(config, name)
    updated = upsert_instance(config, InstanceConfig(name=name, base_url=base_url, auth=existing.auth if existing else None))
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
    "in order and picks the first session accepted by Superset. "
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
    if instance.auth and instance.auth.mode == "api_key":
        typer.echo("API-key mode does not import browser cookies. Use 'auth api-key set' or 'auth api-key clear'.", err=True)
        raise typer.Exit(code=1)
    storage_state_path = get_storage_state_path(state_dir=state_dir, instance_name=instance_name)

    def validate_imported_state(path: Path) -> bool:
        client = _client(instance=instance, storage_state_path=path)
        try:
            client.get_current_user()
            return True
        except AuthExpiredError:
            return False
        finally:
            client.close()

    try:
        summary = import_browser_cookies(
            base_url=instance.base_url,
            storage_state_path=storage_state_path,
            browser=browser,
            validate=validate_imported_state,
        )
    except NoCookiesFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    except httpx.RequestError as exc:
        typer.echo(
            f"The imported cookie could not be validated because of a network error: {exc}. "
            "The auth state was preserved."
        )
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
    instance = _require_instance(ctx, instance_name)
    if instance.auth and instance.auth.mode == "api_key":
        typer.echo("Use 'auth api-key clear' to remove the binding; server-side key revocation is separate.", err=True)
        raise typer.Exit(code=1)
    instance_dir = get_instance_dir(state_dir=state_dir, instance_name=instance_name)
    if not instance_dir.exists():
        typer.echo(f"No saved auth state for instance '{instance_name}'. Nothing to remove.")
        raise typer.Exit(code=1)
    remove_auth_state(state_dir=state_dir, instance_name=instance_name)
    if as_json:
        typer.echo(json.dumps({"removed_auth_state": instance_name}, separators=(",", ":")))
        return
    typer.echo(f"Removed auth state for instance '{instance_name}'.")


@jwt_app.command("login")
def auth_jwt_login(
    ctx: typer.Context, instance_name: str,
    username_env: Annotated[str | None, typer.Option("--username-env")] = None,
    password_env: Annotated[str | None, typer.Option("--password-env")] = None,
    provider: Annotated[str | None, typer.Option("--provider", help="db or ldap only.")] = None,
    state_dir: Annotated[Path, typer.Option("--state-dir")] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    existing = instance.auth.jwt if instance.auth and instance.auth.jwt else None
    try:
        settings = JWTSettings(username_env=username_env or (existing.username_env if existing else ""),
                               password_env=password_env or (existing.password_env if existing else ""),
                               provider=provider or (existing.provider if existing else "db"))
        username, password = os.environ.get(settings.username_env, ""), os.environ.get(settings.password_env, "")
        if not username or not password:
            raise ValueError("Missing credential environment variables.")
    except ValueError:
        typer.echo("JWT login needs populated --username-env/--password-env bindings and provider db or ldap.", err=True)
        raise typer.Exit(code=1)
    path = get_instance_dir(state_dir=state_dir, instance_name=instance_name) / "jwt-state.json"
    try:
        with _api_errors():
            login_jwt(instance.base_url, path, username=username, password=password, provider=settings.provider, timeout=HTTP_TIMEOUT.get())
        config = load_config(_get_config_path(ctx))
        instance.auth = AuthConfig(mode="jwt", jwt=settings)
        save_config(upsert_instance(config, instance), _get_config_path(ctx))
    except (ValueError, OSError):
        typer.echo("Could not validate or save JWT state.", err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps(jwt_status(path)) if as_json else "Saved JWT authentication state.")


@jwt_app.command("refresh")
def auth_jwt_refresh(
    ctx: typer.Context, instance_name: str,
    state_dir: Annotated[Path, typer.Option("--state-dir")] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    path = get_instance_dir(state_dir=state_dir, instance_name=instance_name) / "jwt-state.json"
    try:
        with _api_errors():
            with httpx.Client(base_url=instance.base_url, follow_redirects=False, timeout=HTTP_TIMEOUT.get()) as http:
                refresh_jwt(http, path)
    except (ValueError, OSError):
        typer.echo("JWT refresh failed; run 'auth jwt login'.", err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps(jwt_status(path)) if as_json else "Refreshed JWT authentication state.")


@jwt_app.command("logout")
def auth_jwt_logout(
    ctx: typer.Context, instance_name: str,
    state_dir: Annotated[Path, typer.Option("--state-dir")] = DEFAULT_STATE_DIR,
) -> None:
    _require_instance(ctx, instance_name)
    path = get_instance_dir(state_dir=state_dir, instance_name=instance_name) / "jwt-state.json"
    try:
        path.unlink(missing_ok=True)
    except OSError:
        typer.echo("Could not remove JWT state.", err=True)
        raise typer.Exit(code=1)
    typer.echo("Removed JWT authentication state; browser state was preserved.")


@auth_app.command("export-playwright")
def auth_export_playwright(
    ctx: typer.Context, instance_name: str,
    output: Annotated[Path, typer.Option("--output", help="New private state file; never overwritten.")],
    state_dir: Annotated[Path, typer.Option("--state-dir")] = DEFAULT_STATE_DIR,
    expiry_unit: Annotated[str, typer.Option("--expiry-unit", help="seconds (browser-cookie3) or milliseconds (legacy input).")] = "seconds",
) -> None:
    _require_instance(ctx, instance_name)
    source = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    if source is None:
        typer.echo("API-key mode has no browser state to export.", err=True)
        raise typer.Exit(code=1)
    try:
        export_playwright_state(source, output, expiry_unit=expiry_unit)
    except (ValueError, OSError):
        typer.echo("Could not export browser state. Check input fields, --expiry-unit, and that --output is a new writable path.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Exported private browser state to {output}.")


api_key_app = InstanceTyper(help="Environment-only API keys for verified compatible server deployments.")
auth_app.add_typer(api_key_app, name="api-key")


@api_key_app.command("set")
def auth_api_key_set(
    ctx: typer.Context, instance_name: str,
    env: Annotated[str, typer.Option("--env", help="Environment variable name, never the key value.")],
    prefix: Annotated[str, typer.Option("--prefix", help="Server's configured API-key prefix.")] = "sst_",
    state_dir: Annotated[Path, typer.Option("--state-dir")] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    try:
        settings = APIKeySettings(env=env, prefix=prefix)
    except ValueError as exc:
        raise typer.BadParameter("Invalid environment variable name or key prefix.") from exc
    with _api_errors():
        with SupersetClient(base_url=instance.base_url, api_key=settings) as client:
            client.request("GET", "/api/v1/me/")
    instance.auth = AuthConfig(mode="api_key", api_key=settings)
    config = load_config(_get_config_path(ctx))
    save_config(upsert_instance(config, instance), _get_config_path(ctx))
    typer.echo(json.dumps({"mode": "api_key", **settings.model_dump()}) if as_json else "Saved validated API-key environment binding; no credential was stored.")


@api_key_app.command("clear")
def auth_api_key_clear(
    ctx: typer.Context, instance_name: str,
    state_dir: Annotated[Path, typer.Option("--state-dir")] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    instance = _require_instance(ctx, instance_name)
    if instance.auth and instance.auth.mode == "api_key":
        instance.auth = None
        config = load_config(_get_config_path(ctx))
        save_config(upsert_instance(config, instance), _get_config_path(ctx))
    mode = instance.auth.mode if instance.auth else "cookie"
    typer.echo(json.dumps({"mode": mode}) if as_json else f"No API-key binding remains; selected mode: {mode}. Saved browser/JWT state was preserved.")


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
    if instance.auth and instance.auth.mode == "api_key":
        settings = instance.auth.api_key
        try:
            available = settings is not None and bool(read_api_key(settings))
        except ValueError:
            available = False
        payload = {"instance": instance.name, "base_url": instance.base_url, "mode": "api_key", "credential_available": available}
        typer.echo(json.dumps(payload) if as_json else f"API-key credential available: {available}; run 'auth validate' to verify server acceptance.")
        return
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    payload = {
        "instance": instance.name,
        "base_url": instance.base_url,
        **(jwt_status(storage_state_path) if instance.auth and instance.auth.mode == "jwt"
           else get_auth_status(storage_state_path=storage_state_path)),
    }
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"Authenticated: {payload['authenticated']}")
    typer.echo(f"Saved storage state: {payload['storage_state_path']}")
    if payload.get("mode") == "jwt":
        typer.echo(f"JWT access expiry: {payload['access_token_exp']}")
        typer.echo(f"JWT refresh expiry: {payload['refresh_token_exp']}")
        return
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", min=0, callback=_validate_list_page, help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", min=1, help="Number of results per page.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by dashboard title using Superset contains matching.")] = None,
    order_column: Annotated[str | None, typer.Option("--order-column", help="Superset list field to order by.")] = None,
    order_direction: Annotated[str | None, typer.Option("--order-direction", help="Sort direction: asc or desc.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            payload = client.list_dashboards(
                **_list_options(filters, columns, all_pages),
                page=page,
                page_size=page_size,
                search=search,
                order_column=order_column,
                order_direction=order_direction,
            )

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if _print_list_projection(payload, columns, as_json):
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            payload = client.get_dashboard(id_or_slug)

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    typer.echo(f"ID: {payload.get('id')}")
    typer.echo(f"Title: {payload.get('dashboard_title')}")
    typer.echo(f"Slug: {payload.get('slug')}")
    typer.echo(f"Published: {payload.get('published')}")


@dashboards_app.command("diff")
def dashboards_diff(
    ctx: typer.Context,
    instance_name: str,
    id_or_slug_a: str,
    id_or_slug_b: str,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
) -> None:
    """Compare two dashboard records field-by-field (identity/timestamp fields ignored)."""
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            a = client.get_dashboard(id_or_slug_a)
            b = client.get_dashboard(id_or_slug_b)
    diffs = diff_dashboard_records(a, b)

    if as_json:
        typer.echo(json.dumps([{"field": f, "a": va, "b": vb} for f, va, vb in diffs], separators=(",", ":")))
        return

    if not diffs:
        typer.echo("No differences.")
        return
    for field, va, vb in diffs:
        typer.echo(f"[{field}]")
        typer.echo(f"  {id_or_slug_a}: {va}")
        typer.echo(f"  {id_or_slug_b}: {vb}")


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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", min=0, callback=_validate_list_page, help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", min=1, help="Number of results per page.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by chart name using Superset contains matching.")] = None,
    order_column: Annotated[str | None, typer.Option("--order-column", help="Superset list field to order by.")] = None,
    order_direction: Annotated[str | None, typer.Option("--order-direction", help="Sort direction: asc or desc.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            payload = client.list_charts(
                **_list_options(filters, columns, all_pages),
                page=page,
                page_size=page_size,
                search=search,
                order_column=order_column,
                order_direction=order_direction,
            )

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if _print_list_projection(payload, columns, as_json):
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", min=0, callback=_validate_list_page, help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", min=1, help="Number of results per page.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by dataset table name using Superset contains matching.")] = None,
    order_column: Annotated[str | None, typer.Option("--order-column", help="Superset list field to order by.")] = None,
    order_direction: Annotated[str | None, typer.Option("--order-direction", help="Sort direction: asc or desc.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            payload = client.list_datasets(
                **_list_options(filters, columns, all_pages),
                page=page,
                page_size=page_size,
                search=search,
                order_column=order_column,
                order_direction=order_direction,
            )

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if _print_list_projection(payload, columns, as_json):
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    state_dir: Annotated[
        Path,
        typer.Option("--state-dir", help="Directory for saved auth state."),
    ] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Return structured JSON output.")] = False,
    page: Annotated[int | None, typer.Option("--page", min=0, callback=_validate_list_page, help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", min=1, help="Number of results per page.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Filter results by database name using Superset contains matching.")] = None,
    order_column: Annotated[str | None, typer.Option("--order-column", help="Superset list field to order by.")] = None,
    order_direction: Annotated[str | None, typer.Option("--order-direction", help="Sort direction: asc or desc.")] = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            payload = client.list_databases(
                **_list_options(filters, columns, all_pages),
                page=page,
                page_size=page_size,
                search=search,
                order_column=order_column,
                order_direction=order_direction,
            )

    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return

    if _print_list_projection(payload, columns, as_json):
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
    columns: list[str] | None = None,
) -> None:
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            payload = list_call(client)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    if _print_list_projection(payload, columns, as_json):
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            payload = get_call(client)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    for line in human_lines(payload):
        typer.echo(line)


_STATE_DIR_OPT = typer.Option("--state-dir", help="Directory for saved auth state.")
_JSON_OPT = typer.Option("--json", help="Return structured JSON output.")
_PAGE_OPT = typer.Option("--page", min=0, callback=_validate_list_page, help="Page index (0-based).")
_PAGE_SIZE_OPT = typer.Option("--page-size", min=1, help="Number of results per page.")
_ORDER_COL_OPT = typer.Option("--order-column", help="Superset list field to order by.")
_ORDER_DIR_OPT = typer.Option("--order-direction", help="Sort direction: asc or desc.")


@dashboards_app.command("export")
@charts_app.command("export")
@datasets_app.command("export")
@databases_app.command("export")
def assets_export(
    ctx: typer.Context, instance_name: str, ids: Annotated[list[int], typer.Argument()],
    output: Annotated[Path, typer.Option("--output", help="Destination ZIP file.")],
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing output file.")] = False,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
) -> None:
    if any(pk < 1 for pk in ids):
        typer.echo("Export requires positive integer IDs.", err=True)
        raise typer.Exit(code=2)
    if output.exists() and not force:
        typer.echo("Output already exists; use --force to overwrite.", err=True)
        raise typer.Exit(code=1)
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    resource = ctx.parent.info_name[:-1]
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            content, content_type, _ = client.export_assets(resource, ids)
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in {"application/zip", "application/octet-stream", "application/x-zip-compressed"} or not zipfile.is_zipfile(io.BytesIO(content)):
        typer.echo("Export response is not a ZIP archive; no file written.", err=True)
        raise typer.Exit(code=1)
    try:
        with output.open("wb" if force else "xb") as destination:
            destination.write(content)
    except OSError as exc:
        typer.echo(f"Could not write export: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Exported {len(ids)} {resource}(s) to {output}.")


@roles_app.command("list")
def security_roles_list(
    ctx: typer.Context, instance_name: str,
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    search: Annotated[str | None, typer.Option("--search")] = None,
) -> None:
    _run_list(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
              columns=columns,
              list_call=lambda c: c.list_roles(search=search, **_list_options(filters, columns, all_pages, page=page, page_size=page_size, order_column=order_column, order_direction=order_direction)), empty_message="No roles found.",
              line_formatter=lambda x: f"{x.get('id')}: {x.get('name')}")


@roles_app.command("get")
def security_roles_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
             get_call=lambda c: c.get_role(pk), human_lines=lambda x: [f"{x.get('id')}: {x.get('name')}"])


@security_app.command("permissions")
def security_permissions(
    ctx: typer.Context, instance_name: str,
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    """Discover permission/resource IDs; never infer grants from role names."""
    _run_list(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
        columns=columns, empty_message="No permission/resource pairs found.",
        list_call=lambda c: c.list_permission_resources(**_list_options(filters, columns, all_pages,
            page=page, page_size=page_size, order_column=order_column, order_direction=order_direction)),
        line_formatter=lambda x: f"{x.get('id')}: {x.get('permission', {}).get('name')} / {x.get('view_menu', {}).get('name')}")


@roles_app.command("permissions")
def security_role_permissions(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    """Inspect stored direct role grants, not complete effective user permissions."""
    _run_get(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
        get_call=lambda c: c.get_role_permissions(pk),
        human_lines=lambda x: [f"{r['id']}: {r['permission_name']} / {r['view_menu_name']}" for r in x["result"]]
            or ["No stored direct role permissions."])


@users_app.command("list")
def security_users_list(
    ctx: typer.Context, instance_name: str,
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    search: Annotated[str | None, typer.Option("--search")] = None,
) -> None:
    _run_list(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
              columns=columns,
              list_call=lambda c: c.list_users(search=search, **_list_options(filters, columns, all_pages, page=page, page_size=page_size, order_column=order_column, order_direction=order_direction)), empty_message="No users found.",
              line_formatter=lambda x: f"{x.get('id')}: {x.get('username')}")


@users_app.command("get")
def security_users_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
             get_call=lambda c: c.get_user(pk), human_lines=lambda x: [f"{x.get('id')}: {x.get('username')}"])


@rls_app.command("list")
def security_rls_list(
    ctx: typer.Context, instance_name: str,
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_list(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
              columns=columns,
              list_call=lambda c: c.list_rls_rules(**_list_options(filters, columns, all_pages, page=page, page_size=page_size, order_column=order_column, order_direction=order_direction)), empty_message="No RLS rules found.",
              line_formatter=lambda x: f"{x.get('id')}: {x.get('name')}")


@rls_app.command("get")
def security_rls_get(
    ctx: typer.Context, instance_name: str, pk: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
             get_call=lambda c: c.get_rls_rule(pk), human_lines=lambda x: [f"{x.get('id')}: {x.get('name')}"])


@explore_app.command("show")
def explore_show(
    ctx: typer.Context, instance_name: str,
    slice_id: Annotated[int, typer.Option("--slice-id", min=1)],
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
             get_call=lambda c: c.get_explore(slice_id), human_lines=lambda x: [json.dumps(x, indent=2)])


@explore_app.command("form-data")
def explore_form_data(
    ctx: typer.Context, instance_name: str, key: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _run_get(ctx=ctx, instance_name=instance_name, state_dir=state_dir, as_json=as_json,
             get_call=lambda c: c.get_explore_form_data(key), human_lines=lambda x: [json.dumps(x, indent=2)])


@annotation_layers_app.command("list")
def annotation_layers_list(
    ctx: typer.Context,
    instance_name: str,
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
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
        columns=columns,
        list_call=lambda c: c.list_annotation_layers(
            **_list_options(filters, columns, all_pages),
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
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
        columns=columns,
        list_call=lambda c: c.list_css_templates(
            **_list_options(filters, columns, all_pages),
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
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
        columns=columns,
        list_call=lambda c: c.list_themes(
            **_list_options(filters, columns, all_pages),
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
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
        columns=columns,
        list_call=lambda c: c.list_tags(
            **_list_options(filters, columns, all_pages),
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
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
        columns=columns,
        list_call=lambda c: c.list_reports(
            **_list_options(filters, columns, all_pages),
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
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
        columns=columns,
        list_call=lambda c: c.list_saved_queries(
            **_list_options(filters, columns, all_pages),
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
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
        columns=columns,
        list_call=lambda c: c.list_queries(
            **_list_options(filters, columns, all_pages),
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
    filters: Annotated[list[str] | None, _LIST_FILTER_OPT] = None,
    columns: Annotated[list[str] | None, _LIST_COLUMNS_OPT] = None,
    all_pages: Annotated[bool, _LIST_ALL_OPT] = False,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    page: Annotated[int | None, _PAGE_OPT] = None,
    page_size: Annotated[int | None, _PAGE_SIZE_OPT] = None,
    order_column: Annotated[str | None, _ORDER_COL_OPT] = None,
    order_direction: Annotated[str | None, _ORDER_DIR_OPT] = None,
) -> None:
    _run_list(
        instance_name=instance_name, state_dir=state_dir, ctx=ctx, as_json=as_json,
        columns=columns,
        list_call=lambda c: c.list_logs(
            **_list_options(filters, columns, all_pages),
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
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
    as_csv: Annotated[bool, typer.Option("--csv", help="CSV tables separated by a blank line; __timestamp in UTC.")] = False,
    time_range: Annotated[str | None, typer.Option("--time-range", help="Override every query's Superset time range.")] = None,
    filters: Annotated[list[str] | None, typer.Option("--filter", help="Append a string equality filter col=value; repeatable.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Load requested queries from source and refresh their cache; requires --allow-write.")] = False,
    allow_write: Annotated[bool, typer.Option("--allow-write", help="Required to actually perform the write. Without it the command is a dry-run. Applies to --force.")] = False,
    cache_info: Annotated[bool, typer.Option("--cache-info", help="Show per-query server cache metadata in human output; JSON/CSV stay unchanged.")] = False,
) -> None:
    if force:
        _require_allow_write(allow_write, action=f"force-refresh chart {pk} results and their cache")
    query_filters = []
    for value in filters or []:
        col, separator, val = value.partition("=")
        if not separator or not col.strip() or not val:
            typer.echo("--filter requires col=value with a nonempty column and value.", err=True)
            raise typer.Exit(code=2)
        query_filters.append({"col": col.strip(), "op": "==", "val": val})
    if time_range is not None and not time_range.strip():
        typer.echo("--time-range must not be empty.", err=True)
        raise typer.Exit(code=2)
    if as_json and as_csv:
        typer.echo("--csv and --json cannot be used together.", err=True)
        raise typer.Exit(code=2)
    instance = _require_instance(ctx, instance_name)
    storage_state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            try:
                options = {"time_range": time_range, "filters": query_filters} if time_range is not None or query_filters else {}
                if force:
                    options["force"] = True
                payload = client.get_chart_data(pk, **options)
            except ValueError as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(code=2) from exc
    queries = payload.get("result") or []
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
    elif as_csv:
        for idx, query in enumerate(queries):
            if idx:
                typer.echo()
            output = io.StringIO()
            writer = csv.writer(output, lineterminator="\n")
            cols = query.get("colnames") or []
            writer.writerow(cols)
            for row in query.get("data") or []:
                values = []
                for col in cols:
                    value = row.get(col)
                    if col == "__timestamp" and isinstance(value, (int, float)) and not isinstance(value, bool):
                        try:
                            value = datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
                        except (OverflowError, OSError, ValueError):
                            pass  # Keep out-of-range values inspectable instead of failing output.
                    values.append(value)
                writer.writerow(values)
            typer.echo(output.getvalue(), nl=False)
    else:
        typer.echo(f"Queries: {len(queries)}")
        for idx, query in enumerate(queries):
            rowcount = query.get("rowcount")
            if rowcount is None:
                rowcount = len(query.get("data") or [])
            cols = query.get("colnames") or []
            typer.echo(f"  [{idx}] rows={rowcount} columns={','.join(cols)}")
            if cache_info:
                hit = query.get("is_cached")
                status = "hit" if hit is True else "miss" if hit is False else "unknown"
                metadata = {key: json.dumps(query[key], ensure_ascii=True) if key in query else "unknown"
                            for key in ("cache_key", "cached_dttm", "cache_timeout")}
                timeout = metadata["cache_timeout"]
                if query.get("cache_timeout") == -1:
                    timeout += " (disabled)"
                typer.echo(f"  [{idx}] cache={status} key={metadata['cache_key']} cached_at={metadata['cached_dttm']} timeout={timeout}")
    successful = [query for query in queries if query.get("status", "success") == "success"]
    if queries and not successful:
        detail = next((query.get("error") for query in queries if query.get("error")), "unknown error")
        typer.echo(f"chart queries failed: {' '.join(str(detail).split())[:300]}", err=True)
        raise typer.Exit(code=1)
    if not any(query.get("data") for query in successful):
        typer.echo("chart returned 0 rows", err=True)
        raise typer.Exit(code=1)


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


def _run_api_key_lifecycle(ctx, instance_name, state_dir, as_json, operation, key_uuid=None):
    instance = _require_instance(ctx, instance_name)
    try:
        state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
        with _client(instance=instance, storage_state_path=state_path) as client:
            method = getattr(client, f"{operation}_api_key" + ("s" if operation == "list" else ""))
            payload = method() if operation == "list" else method(key_uuid)
    except (AuthExpiredError, NotFoundError, httpx.HTTPError, ValueError, OSError):
        # Lifecycle responses/errors are untrusted; never forward their bodies.
        if operation == "revoke":
            typer.echo(f"API-key revocation unverified for {key_uuid}; reconcile using an independent authorized credential before retrying.", err=True)
        else:
            typer.echo("Could not read API-key metadata; check authentication, ownership, ApiKey permissions and server capability.", err=True)
        raise typer.Exit(code=1)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
    elif operation == "revoke":
        typer.echo(f"API-key revocation verified for {key_uuid} by stored metadata.")
    else:
        items = payload["result"] if operation == "list" else [payload["result"]]
        if not items:
            typer.echo("No API keys for the current user.")
        for item in items:
            typer.echo(json.dumps(item, ensure_ascii=True))


def _validate_api_key_uuid(key_uuid: str) -> str:
    try:
        return SupersetClient.validate_api_key_uuid(key_uuid)
    except ValueError:
        raise typer.BadParameter("API key identifier must be a UUID.") from None


@api_key_app.command("list")
def auth_api_key_list(
    ctx: typer.Context, instance_name: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    """List current-user key metadata only; no pagination or plaintext secrets."""
    _run_api_key_lifecycle(ctx, instance_name, state_dir, as_json, "list")


@api_key_app.command("get")
def auth_api_key_get(
    ctx: typer.Context, instance_name: str, key_uuid: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    """Read current-user key metadata by UUID, never the key value."""
    key_uuid = _validate_api_key_uuid(key_uuid)
    _run_api_key_lifecycle(ctx, instance_name, state_dir, as_json, "get", key_uuid)


@api_key_app.command("revoke")
def auth_api_key_revoke(
    ctx: typer.Context, instance_name: str, key_uuid: str,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    """Revoke a current-user key; successful metadata read-back is required."""
    _require_allow_write(allow_write, action=f"revoke API key {key_uuid}")
    key_uuid = _validate_api_key_uuid(key_uuid)
    _run_api_key_lifecycle(ctx, instance_name, state_dir, as_json, "revoke", key_uuid)


@api_key_app.command("create")
def auth_api_key_create(
    ctx: typer.Context, instance_name: str,
    name: Annotated[str, typer.Option("--name", help="Current-user key name, at most 180 characters.")],
    expires_on: Annotated[str, typer.Option("--expires-on", help="Timezone-aware future ISO expiry within 90 days.")],
    operation_id: Annotated[str, typer.Option("--operation-id", help="Unique attempt UUID; reconcile before retrying.")],
    server_timezone: Annotated[str, typer.Option("--server-timezone", help="Independently verified server local-clock IANA timezone.")],
    secret_output: Annotated[bool, typer.Option("--secret-output", help="Separate explicit opt-in: emit only the one-time key to stdout; metadata goes to stderr. Required for issuance.")] = False,
    prefix: Annotated[str, typer.Option("--prefix", help="Expected server API-key prefix.")] = "sst_",
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    """Create for the current user; storage and pipeline failure checks belong to the caller."""
    import sys
    from contextlib import redirect_stdout
    with redirect_stdout(sys.stderr):
        _require_allow_write(allow_write, action="create a current-user API key")
    if not secret_output:
        typer.echo("Issuance also requires --secret-output; the one-time key must not be silently discarded.", err=True)
        raise typer.Exit(code=1)
    if as_json:
        raise typer.BadParameter("--json cannot be combined with --secret-output; stdout contains only the key.")
    from superset_cli.key_issuance import creation_request, create_and_emit_key
    from superset_cli.jwt_auth import require_jwt_tls
    try:
        body, operation_id = creation_request(name, expires_on, operation_id, prefix, server_timezone)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None
    with redirect_stdout(sys.stderr):
        instance = _require_instance(ctx, instance_name)
    payload = None
    try:
        require_jwt_tls(instance.base_url)
        with redirect_stdout(sys.stderr):
            state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
        with _client(instance=instance, storage_state_path=state_path) as client:
            payload = create_and_emit_key(client, body=body, operation_id=operation_id,
                                          prefix=prefix, server_timezone=server_timezone)
    except typer.Exit:
        raise
    except (Exception, KeyboardInterrupt):
        if payload is None:
            payload = {"operation_id": operation_id, "key_uuid": None, "owner_id": None,
                       "emitted": False, "revocation_verified": None, "outcome": "preflight_failed"}
        else:
            typer.echo("Outcome recorded before client shutdown failed; inspect the recovery identifiers.", err=True)
    typer.echo(json.dumps(payload, separators=(",", ":")), err=True)
    if not payload["emitted"]:
        typer.echo("Issuance/output failed or is unverified; any delivery is uncertain. Reconcile the operation/key IDs using a surviving authorized credential before retrying. No mutation was replayed.", err=True)
        raise typer.Exit(code=1)


@cache_app.command("invalidate")
def cache_invalidate(
    ctx: typer.Context,
    instance_name: str,
    dataset_ids: Annotated[list[int], typer.Option("--dataset", min=1, help="Positive numeric dataset ID; repeat to target multiple datasets.")],
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    _require_allow_write(allow_write, action=f"invalidate tracked cache entries for datasets {', '.join(map(str, dataset_ids))}")
    instance = _require_instance(ctx, instance_name)
    state_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=state_path) as client:
            payload = client.invalidate_dataset_cache(dataset_ids)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
    else:
        typer.echo(f"Cache invalidation request accepted for datasets {', '.join(map(str, payload['dataset_ids']))}; eviction not verified.")
        typer.echo("Requires tracked keys and compatible cache/data-cache backends; verify normal non-forced results before claiming eviction.")


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
        with _client(instance=instance, storage_state_path=storage_state_path) as client:
            payload = call(client)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
        return
    typer.echo(human_line)


def _run_owner_call(ctx: typer.Context, instance_name: str, state_dir: Path, as_json: bool, call) -> None:
    resource = ctx.parent.info_name[:-1]
    instance = _require_instance(ctx, instance_name)
    storage = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage) as client:
            try:
                payload = call(client, resource)
            except ValueError as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(code=1) from exc
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
    elif "count" in payload:
        typer.echo(f"Count: {payload['count']}")
        for owner in payload["result"]:
            typer.echo(f"{owner['value']}: {owner['text']}")
        if not payload["result"]:
            typer.echo("No eligible owners.")
    else:
        if "write_performed" in payload:
            if payload["write_performed"] is None:
                typer.echo("Owner write outcome is unknown.")
            else:
                typer.echo("Owner update sent." if payload["write_performed"] else "No owner change needed (no PUT).")
        typer.echo(f"Effective owners of {resource} {payload['id']}:" if payload["owners"] is not None
                   else "Effective owners could not be verified.")
        if payload["owners"] is not None:
            for owner in payload["owners"]:
                name = " ".join(str(owner.get(key) or "") for key in ("first_name", "last_name")).strip()
                typer.echo(f"{owner['id']}: {name}")
            if not payload["owners"]:
                typer.echo("No owners.")
    if payload.get("warning"):
        typer.echo(payload["warning"], err=True)
        raise typer.Exit(code=1)


@dashboards_app.command("owners")
@charts_app.command("owners")
def resource_owners(
    ctx: typer.Context, instance_name: str, identifier: str,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    """Inspect this resource's owners, not its creators or other resources' owners."""
    _run_owner_call(ctx, instance_name, state_dir, as_json, lambda c, r: c.get_owners(r, identifier))


@dashboards_app.command("owner-candidates")
@charts_app.command("owner-candidates")
def owner_candidates(
    ctx: typer.Context, instance_name: str,
    search: Annotated[str | None, typer.Option("--search", help="Server-filtered name/username search.")] = None,
    page: Annotated[int | None, typer.Option("--page", min=0, help="Page index (0-based).")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size", min=1)] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
) -> None:
    """Discover eligible owners through this resource's permission-filtered related API."""
    _run_owner_call(ctx, instance_name, state_dir, as_json,
                    lambda c, r: c.get_owner_candidates(r, search=search, page=page, page_size=page_size))


@dashboards_app.command("owners-set")
@charts_app.command("owners-set")
@dashboards_app.command("owners-add")
@charts_app.command("owners-add")
@dashboards_app.command("owners-remove")
@charts_app.command("owners-remove")
def resource_owners_change(
    ctx: typer.Context, instance_name: str, identifier: str,
    owner_ids: Annotated[list[int] | None, typer.Option("--owner-id", min=1, help="Positive user ID; repeat for multiple owners.")] = None,
    clear: Annotated[bool, typer.Option("--clear", help="Explicit empty replacement or permission to remove the last owner; not for add.")] = False,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    """Set/add/remove owners and verify effective state. Non-admin callers may be retained.

    Add/remove is non-atomic read-modify-write. Never blindly retry a sent mutation.
    """
    operation = ctx.info_name.rsplit("-", 1)[1]
    _require_allow_write(allow_write, action=f"{operation} owners of {ctx.parent.info_name[:-1]} {identifier} on instance '{instance_name}'")
    _run_owner_call(ctx, instance_name, state_dir, as_json,
                    lambda c, r: c.change_owners(r, identifier, operation=operation, owner_ids=owner_ids, clear=clear))


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
    if instance.auth and instance.auth.mode in {"jwt", "api_key"}:
        storage_path = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
        with _api_errors():
            with _client(instance=instance, storage_state_path=storage_path) as client:
                client.request("GET", "/api/v1/me/")
                payload = client.request(method, path, params=params, json_body=payload_body)
        typer.echo(json.dumps(payload, separators=(",", ":") if as_json else None, indent=None if as_json else 2))
        return
    storage_path = get_storage_state_path(state_dir=state_dir, instance_name=instance_name)

    def validate(candidate: Path) -> bool:
        with _client(instance=instance, storage_state_path=candidate) as client:
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
        with _client(instance=instance, storage_state_path=storage_path) as client:
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
    clear_query_context: Annotated[
        bool,
        typer.Option(
            "--clear-query-context",
            help=(
                "Also set query_context to null. Superset keeps a stale saved "
                "query_context when only params change, which can pin old "
                "filters/metrics; use this when editing a chart's params."
            ),
        ),
    ] = False,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    if clear_query_context and body is None and file is None:
        payload_body: dict = {}
    else:
        payload_body = _load_body(body, file)
    if clear_query_context:
        payload_body = {**payload_body, "query_context": None}
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

@roles_app.command("permissions-set")
def security_role_permissions_set(
    ctx: typer.Context, instance_name: str, pk: str,
    body: Annotated[str | None, _BODY_OPT] = None,
    file: Annotated[Path | None, _FILE_OPT] = None,
    state_dir: Annotated[Path, _STATE_DIR_OPT] = DEFAULT_STATE_DIR,
    as_json: Annotated[bool, _JSON_OPT] = False,
    allow_write: Annotated[bool, _ALLOW_WRITE_OPT] = False,
) -> None:
    """Replace all direct grants using explicit expected identity/current pairs and desired pairs."""
    _require_allow_write(allow_write, action=f"replace all permissions of role {pk}")
    payload_body = _load_body(body, file)
    instance = _require_instance(ctx, instance_name)
    storage = _require_storage_state(instance_name=instance_name, state_dir=state_dir)
    with _api_errors():
        with _client(instance=instance, storage_state_path=storage) as client:
            payload = client.set_role_permissions(pk, payload_body)
    if as_json:
        typer.echo(json.dumps(payload, separators=(",", ":")))
    else:
        typer.echo("Stored direct grants verified." if payload["matches_requested"] else "Stored direct grants are not verified.")
        for row in payload["permissions"] or []:
            typer.echo(f"{row['id']}: {row['permission_name']} / {row['view_menu_name']}")
    if payload["warning"]:
        typer.echo(payload["warning"], err=True)
        raise typer.Exit(code=1)


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
