"""Instance defaults and a narrow positional-arity adapter for existing commands."""
import os

import typer
from typer.core import TyperArgument, TyperCommand, TyperOption

from superset_cli.config import get_instance, load_config


def resolve_instance_name(config, *, positional=None, override=None):
    candidates = [positional, override, os.environ.get("SUPERSET_CLI_INSTANCE") or None, config.default_instance]
    selected = next((value for value in candidates if value is not None), None)
    if selected is None and len(config.instances) == 1:
        selected = config.instances[0].name
    if selected is None:
        names = ", ".join(item.name for item in config.instances) or "none"
        raise ValueError(f"Select an instance with --instance or 'instances use'. Configured: {names}.")
    if get_instance(config, selected) is None:
        raise ValueError(f"Selected instance '{selected}' is not configured.")
    return selected


class InstanceCommand(TyperCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for param in self.params:
            if isinstance(param, TyperArgument) and param.name == "instance_name":
                param.required = False
                param.default = None

    def parse_args(self, ctx, args):
        arguments = [p for p in self.params if isinstance(p, TyperArgument)]
        if not any(p.name == "instance_name" for p in arguments):
            return super().parse_args(ctx, args)
        options = [p for p in self.params if isinstance(p, TyperOption)]
        help_option = self.get_help_option(ctx)
        if help_option:
            options.append(help_option)
        scanner = TyperCommand(self.name, params=options, add_help_option=False)
        parsed, positional, _ = scanner.make_parser(ctx).parse_args(list(args))
        if help_option and parsed.get(help_option.name):
            return super().parse_args(ctx, args)
        others = [p for p in arguments if p.name != "instance_name"]
        required = sum(max(p.nargs, 1) for p in others if p.required)
        variadic = any(p.nargs == -1 for p in others)
        omitted = len(positional) == required
        if variadic and len(positional) >= required:
            config = load_config((ctx.obj or {}).get("config_path"))
            numeric = positional and positional[0].isdigit()
            override = (ctx.obj or {}).get("instance_override")
            if numeric and get_instance(config, positional[0]) and not override and len(positional) > required:
                raise typer.BadParameter("Ambiguous numeric instance/export IDs; use global --instance and supply only IDs.")
            omitted = bool(numeric) and (override is not None or get_instance(config, positional[0]) is None or len(positional) == required)
        if omitted:
            config = load_config((ctx.obj or {}).get("config_path"))
            try:
                selected = resolve_instance_name(config, override=(ctx.obj or {}).get("instance_override"))
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc
            args = [selected, *args]
        return super().parse_args(ctx, args)


class InstanceTyper(typer.Typer):
    def command(self, *args, **kwargs):
        kwargs.setdefault("cls", InstanceCommand)
        return super().command(*args, **kwargs)
