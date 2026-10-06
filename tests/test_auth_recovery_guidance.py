from http.cookiejar import CookieJar
import pytest

from superset_cli import auth
from superset_cli.auth import NoCookiesFoundError, import_browser_cookies


@pytest.mark.parametrize("browser", ["firefox", "zen"])
def test_missing_persisted_cookies_do_not_claim_memory_session_detection(monkeypatch, tmp_path, browser):
    monkeypatch.setitem(auth._LOADERS, browser, lambda host: CookieJar())
    with pytest.raises(NoCookiesFoundError) as error:
        import_browser_cookies(base_url="https://superset.example.com", storage_state_path=tmp_path / "state.json", browser=browser)
    message = str(error.value)
    assert "persisted" in message
    assert "possible" in message
    assert "Chrome" in message
    assert "cannot detect" in message
