from pathlib import Path

import yaml

from superset_cli.models import Config, InstanceConfig


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "superset-cli" / "config.yaml"
DEFAULT_STATE_DIR = Path.home() / ".local" / "share" / "superset-cli"


def load_config(path: Path | None = None) -> Config:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return Config(instances=[])

    raw = yaml.safe_load(config_path.read_text()) or {}
    return Config.model_validate(raw)


def save_config(config: Config, path: Path | None = None) -> Path:
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config.model_dump(mode="json", exclude_none=True), sort_keys=False))
    return config_path


def upsert_instance(config: Config, instance: InstanceConfig) -> Config:
    instances = [existing for existing in config.instances if existing.name != instance.name]
    instances.append(instance)
    instances.sort(key=lambda existing: existing.name)
    return config.model_copy(update={"instances": instances})


def get_instance(config: Config, name: str) -> InstanceConfig | None:
    return next((instance for instance in config.instances if instance.name == name), None)


def remove_instance(config: Config, name: str) -> Config:
    instances = [i for i in config.instances if i.name != name]
    default = None if config.default_instance == name else config.default_instance
    return config.model_copy(update={"instances": instances, "default_instance": default})
