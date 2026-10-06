import json
import stat

import pytest
from http.cookiejar import Cookie

from superset_cli import auth
from superset_cli.cli import app
from typer.testing import CliRunner


def test_playwright_export_cli(instance_setup, tmp_path):
    config, state = instance_setup
    output = tmp_path / "playwright.json"
    result = CliRunner().invoke(app, ["--config", str(config), "auth", "export-playwright", "prod", "--state-dir", str(state), "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_text()) == {"cookies": [], "origins": []}
    assert "synthetic" not in result.output


@pytest.mark.parametrize("expiry,unit,expected", [(None,"seconds",-1),(0,"seconds",-1),(-1,"seconds",-1),
    (1893456000,"seconds",1893456000),(1893456000000,"milliseconds",1893456000)])
def test_playwright_export(tmp_path, expiry, unit, expected):
    source, output = tmp_path / "storage-state.json", tmp_path / "browser-state.json"
    original = {"cookies": [{"name":"session", "value":"synthetic", "domain":"superset.example.com",
                            "path":"/", "expires":expiry, "secure":True, "httpOnly":True, "sameSite":"Strict"}], "origins":[]}
    source.write_text(json.dumps(original))
    auth.export_playwright_state(source, output, expiry_unit=unit)
    payload = json.loads(output.read_text())
    assert payload["cookies"][0]["expires"] == expected
    assert payload["cookies"][0]["secure"] is True
    assert payload["cookies"][0]["httpOnly"] is True
    assert payload["cookies"][0]["sameSite"] == "Strict"
    assert json.loads(source.read_text()) == original
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        auth.export_playwright_state(source, output, expiry_unit=unit)


@pytest.mark.parametrize("expiry", [float("nan"), float("inf"), -2, "bad", True, 1e20])
def test_playwright_export_invalid_expiry_does_not_write(tmp_path, expiry):
    source, output = tmp_path / "state.json", tmp_path / "out.json"
    source.write_text(json.dumps({"cookies":[{"name":"session","value":"synthetic","domain":"example.com","path":"/","expires":expiry}]}))
    with pytest.raises(ValueError):
        auth.export_playwright_state(source, output)
    assert not output.exists()


def test_import_preserves_cookie_attributes():
    cookie = Cookie(0,"session","synthetic",None,False,"example.com",True,False,"/",True,True,None,True,None,None,
                    {"HTTPOnly":"", "SameSite":"Lax"},False)
    result = auth._serialise_cookie(cookie)
    assert result["httpOnly"] is True
    assert result["secure"] is True
    assert result["sameSite"] == "Lax"
