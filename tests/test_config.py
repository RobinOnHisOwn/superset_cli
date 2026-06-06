from pathlib import Path

from superset_agent_cli.config import Config, load_config


def test_load_config_returns_empty_when_file_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.yaml")

    assert config == Config(instances=[])


def test_load_config_reads_instances_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
instances:
  - name: prod
    base_url: https://superset.example.com
""".strip()
    )

    config = load_config(config_path)

    assert len(config.instances) == 1
    assert config.instances[0].name == "prod"
    assert config.instances[0].base_url == "https://superset.example.com"
