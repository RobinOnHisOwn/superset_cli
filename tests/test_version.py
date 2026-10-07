from typer.testing import CliRunner
from superset_cli.cli import app


def test_version_is_available_without_config_or_network():
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "superset-cli 0.3.1"
