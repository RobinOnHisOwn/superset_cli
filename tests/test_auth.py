import json
from http.cookiejar import Cookie, CookieJar
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from fakes import FakeSupersetClient
from superset_cli.cli import app
from superset_cli.client import AuthExpiredError

runner = CliRunner()


@pytest.fixture(autouse=True)
def valid_superset_client(monkeypatch):
    clients = []

    class ValidClient(FakeSupersetClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            clients.append(self)

    monkeypatch.setattr("superset_cli.cli.SupersetClient", ValidClient)
    return clients


def _add_prod_instance(config_path: Path) -> None:
    runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "instances",
            "add",
            "prod",
            "https://superset.example.com",
        ],
    )


def _make_cookie(name: str, value: str, domain: str, *, expires: int | None = 9999999999, path: str = "/") -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path=path,
        path_specified=True,
        secure=True,
        expires=expires,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def _jar(*cookies: Cookie) -> CookieJar:
    jar = CookieJar()
    for c in cookies:
        jar.set_cookie(c)
    return jar


def test_auth_login_requires_known_instance(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    result = runner.invoke(app, ["--config", str(config_path), "auth", "login", "prod"])

    assert result.exit_code == 1
    assert "Unknown instance 'prod'" in result.stdout


def test_auth_login_rejects_unknown_browser(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path),
            "auth", "login", "prod",
            "--state-dir", str(state_dir),
            "--browser", "netscape",
        ],
    )

    assert result.exit_code != 0
    out = (result.stdout or "") + (result.stderr or "")
    assert "netscape" in out


def test_auth_login_chrome_writes_storage_state(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    jar = _jar(
        _make_cookie("session", "abc123", "superset.example.com", expires=1893456000),
        _make_cookie("csrftoken", "xyz", "superset.example.com", expires=1893456000),
    )
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", lambda **kwargs: jar)

    result = runner.invoke(
        app,
        [
            "--config", str(config_path),
            "auth", "login", "prod",
            "--state-dir", str(state_dir),
            "--browser", "chrome",
        ],
    )

    assert result.exit_code == 0
    storage = state_dir / "prod" / "storage-state.json"
    assert storage.exists()
    data = json.loads(storage.read_text())
    assert {c["name"] for c in data["cookies"]} == {"session", "csrftoken"}
    assert data["origins"] == []


def test_auth_login_filters_to_target_host(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    jar = _jar(
        _make_cookie("session", "keep", "superset.example.com"),
        _make_cookie("unrelated", "drop", "other.example.com"),
        _make_cookie("sibling", "drop", "billing.example.com"),
    )
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", lambda **kwargs: jar)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 0
    data = json.loads((state_dir / "prod" / "storage-state.json").read_text())
    names = {c["name"] for c in data["cookies"]}
    assert names == {"session"}


def test_auth_login_includes_parent_domain_cookies(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    runner.invoke(
        app,
        ["--config", str(config_path), "instances", "add", "raw", "https://superset-raw.example.com"],
    )

    jar = _jar(
        _make_cookie("session", "host", "superset-raw.example.com"),
        _make_cookie("sso", "parent", ".example.com"),
        _make_cookie("other", "drop", "elsewhere.com"),
    )
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", lambda **kwargs: jar)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "raw", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 0
    data = json.loads((state_dir / "raw" / "storage-state.json").read_text())
    names = {c["name"] for c in data["cookies"]}
    assert names == {"session", "sso"}


def test_auth_login_no_cookies_found_errors(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", lambda **kwargs: _jar())

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 1
    assert "No Superset session found" in result.stdout
    assert "superset.example.com" in result.stdout
    assert not (state_dir / "prod" / "storage-state.json").exists()


def test_auth_login_auto_picks_first_browser_with_cookies(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    def chrome_raises(**kwargs):
        raise RuntimeError("chrome not installed")

    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", chrome_raises)
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.edge", lambda **kwargs: _jar())
    monkeypatch.setattr(
        "superset_cli.auth.browser_cookie3.brave",
        lambda **kwargs: _jar(_make_cookie("session", "from-brave", "superset.example.com")),
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["browser_used"] == "brave"
    assert payload["cookie_count"] == 1


def test_auth_login_json_output(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    jar = _jar(_make_cookie("session", "abc", "superset.example.com"))
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", lambda **kwargs: jar)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "instance": "prod",
        "base_url": "https://superset.example.com",
        "browser_used": "chrome",
        "cookie_count": 1,
        "storage_state_path": str(state_dir / "prod" / "storage-state.json"),
    }


def test_auth_login_zen_uses_firefox_loader(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    zen_cookies_path = tmp_path / "zen-cookies.sqlite"
    zen_cookies_path.write_bytes(b"")

    monkeypatch.setattr("superset_cli.auth._resolve_zen_cookies_path", lambda: zen_cookies_path)

    captured = {}

    def fake_firefox(**kwargs):
        captured["cookie_file"] = kwargs.get("cookie_file")
        return _jar(_make_cookie("session", "from-zen", "superset.example.com"))

    monkeypatch.setattr("superset_cli.auth.browser_cookie3.firefox", fake_firefox)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "zen", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["browser_used"] == "zen"
    assert captured["cookie_file"] == str(zen_cookies_path)


def test_auth_login_explicit_browser_surfaces_loader_failure(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    def chrome_raises(**kwargs):
        raise RuntimeError("keychain denied")

    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", chrome_raises)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 1
    assert "No Superset session found" in result.stdout
    assert "chrome" in result.stdout
    assert "keychain denied" in result.stdout
    assert not (state_dir / "prod" / "storage-state.json").exists()


def test_auth_login_writes_storage_state_with_owner_only_perms(monkeypatch, tmp_path: Path) -> None:
    import stat

    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    jar = _jar(_make_cookie("session", "abc", "superset.example.com"))
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", lambda **kwargs: jar)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 0
    storage = state_dir / "prod" / "storage-state.json"
    mode = storage.stat().st_mode
    assert stat.S_IMODE(mode) == 0o600, f"expected 0600, got {oct(stat.S_IMODE(mode))}"


def test_auth_login_zen_picks_most_recently_modified_profile(monkeypatch, tmp_path: Path) -> None:
    import os

    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    fake_zen_root = tmp_path / "zen-root"
    older = fake_zen_root / "old.default" / "cookies.sqlite"
    newer = fake_zen_root / "new.default" / "cookies.sqlite"
    older.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    older.write_bytes(b"")
    newer.write_bytes(b"")
    os.utime(older, (1_000_000_000, 1_000_000_000))
    os.utime(newer, (2_000_000_000, 2_000_000_000))

    monkeypatch.setattr("superset_cli.auth._zen_profile_roots", lambda: [fake_zen_root])

    captured = {}

    def fake_firefox(**kwargs):
        captured["cookie_file"] = kwargs.get("cookie_file")
        return _jar(_make_cookie("session", "abc", "superset.example.com"))

    monkeypatch.setattr("superset_cli.auth.browser_cookie3.firefox", fake_firefox)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "zen"],
    )

    assert result.exit_code == 0
    assert captured["cookie_file"] == str(newer)


def test_auth_login_auto_no_cookies_includes_all_loader_errors(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    def chrome_raises(**kwargs):
        raise RuntimeError("keychain denied")

    def edge_raises(**kwargs):
        raise RuntimeError("edge not installed")

    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", chrome_raises)
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.edge", edge_raises)
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.brave", lambda **kwargs: _jar())
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.firefox", lambda **kwargs: _jar())
    monkeypatch.setattr("superset_cli.auth._resolve_zen_cookies_path", lambda: None)
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.safari", lambda **kwargs: _jar())

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir)],
    )

    assert result.exit_code == 1
    assert "No Superset session found" in result.stdout
    assert "chrome: keychain denied" in result.stdout
    assert "edge: edge not installed" in result.stdout


def test_auth_login_auto_skips_rejected_cookie_and_uses_next_browser(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)
    monkeypatch.setattr(
        "superset_cli.auth.browser_cookie3.chrome",
        lambda **kwargs: _jar(_make_cookie("session", "stale", "superset.example.com")),
    )
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.edge", lambda **kwargs: _jar())
    monkeypatch.setattr(
        "superset_cli.auth.browser_cookie3.brave",
        lambda **kwargs: _jar(_make_cookie("session", "valid", "superset.example.com")),
    )
    clients = []

    class CandidateClient(FakeSupersetClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            clients.append(self)

        def get_current_user(self) -> dict:
            cookies = json.loads(self.storage_state_path.read_text())["cookies"]
            if next(cookie["value"] for cookie in cookies if cookie["name"] == "session") == "stale":
                raise AuthExpiredError("Session expired")
            return super().get_current_user()

    monkeypatch.setattr("superset_cli.cli.SupersetClient", CandidateClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["browser_used"] == "brave"
    assert len(clients) == 2
    assert all(client.closed for client in clients)
    cookies = json.loads((state_dir / "prod" / "storage-state.json").read_text())["cookies"]
    assert next(cookie["value"] for cookie in cookies if cookie["name"] == "session") == "valid"


def test_auth_login_validates_imported_session_and_closes_client(
    monkeypatch, tmp_path: Path, valid_superset_client
) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)
    monkeypatch.setattr(
        "superset_cli.auth.browser_cookie3.chrome",
        lambda **kwargs: _jar(_make_cookie("session", "valid", "superset.example.com")),
    )

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 0
    assert len(valid_superset_client) == 1
    assert valid_superset_client[0].closed is True


def test_auth_login_rejected_session_removes_imported_state(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)
    monkeypatch.setattr(
        "superset_cli.auth.browser_cookie3.chrome",
        lambda **kwargs: _jar(_make_cookie("session", "stale", "superset.example.com")),
    )

    class RejectedClient(FakeSupersetClient):
        def get_current_user(self) -> dict:
            raise AuthExpiredError("Session expired")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", RejectedClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 1
    assert "found in chrome, but Superset rejected it" in result.stdout
    assert not (state_dir / "prod").exists()


def test_auth_login_network_failure_preserves_imported_state(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)
    monkeypatch.setattr(
        "superset_cli.auth.browser_cookie3.chrome",
        lambda **kwargs: _jar(_make_cookie("session", "unknown", "superset.example.com")),
    )

    class NetworkClient(FakeSupersetClient):
        def get_current_user(self) -> dict:
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("superset_cli.cli.SupersetClient", NetworkClient)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 1
    assert "could not be validated" in result.stdout
    assert (state_dir / "prod" / "storage-state.json").exists()


def test_auth_login_human_output(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    _add_prod_instance(config_path)

    jar = _jar(_make_cookie("session", "abc", "superset.example.com"))
    monkeypatch.setattr("superset_cli.auth.browser_cookie3.chrome", lambda **kwargs: jar)

    result = runner.invoke(
        app,
        ["--config", str(config_path), "auth", "login", "prod", "--state-dir", str(state_dir), "--browser", "chrome"],
    )

    assert result.exit_code == 0
    assert "chrome" in result.stdout
    assert "1 cookie" in result.stdout
    assert str(state_dir / "prod" / "storage-state.json") in result.stdout
