import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from http.cookiejar import Cookie, CookieJar
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import browser_cookie3

from superset_cli.client import load_storage_state


SUPPORTED_BROWSERS: tuple[str, ...] = (
    "auto",
    "chrome",
    "edge",
    "brave",
    "firefox",
    "zen",
    "safari",
)
DEFAULT_BROWSER = "auto"
_AUTO_ORDER: tuple[str, ...] = ("chrome", "edge", "brave", "firefox", "zen", "safari")


class NoCookiesFoundError(Exception):
    pass


def get_instance_dir(*, state_dir: Path, instance_name: str) -> Path:
    return state_dir / instance_name


def get_storage_state_path(*, state_dir: Path, instance_name: str) -> Path:
    return get_instance_dir(state_dir=state_dir, instance_name=instance_name) / "storage-state.json"


def get_auth_status(*, storage_state_path: Path) -> dict:
    if not storage_state_path.exists():
        return {
            "authenticated": False,
            "storage_state_path": str(storage_state_path),
            "cookie_count": 0,
            "earliest_cookie_expiry": None,
            "expired": False,
            "session_only": True,
        }

    state = load_storage_state(storage_state_path)
    positive_expiries = [c.expires for c in state.cookies if c.expires is not None and c.expires > 0]
    earliest = min(positive_expiries) if positive_expiries else None
    expired = earliest is not None and earliest < time.time()
    return {
        "authenticated": True,
        "storage_state_path": str(storage_state_path),
        "cookie_count": len(state.cookies),
        "earliest_cookie_expiry": earliest,
        "expired": expired,
        "session_only": earliest is None,
    }


def format_expiry(value: float | None) -> str:
    if value is None:
        return "session-only"
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def remove_auth_state(*, state_dir: Path, instance_name: str) -> Path:
    instance_dir = get_instance_dir(state_dir=state_dir, instance_name=instance_name)
    shutil.rmtree(instance_dir, ignore_errors=True)
    return instance_dir


def _zen_profile_roots() -> list[Path]:
    if sys.platform == "darwin":
        return [Path.home() / "Library" / "Application Support" / "zen" / "Profiles"]
    if sys.platform.startswith("linux"):
        return [Path.home() / ".zen", Path.home() / ".var/app/io.github.zen_browser.zen/.zen"]
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        return [Path(appdata) / "zen" / "Profiles"] if appdata else []
    return []


def _resolve_zen_cookies_path() -> Path | None:
    candidates: list[Path] = []
    for root in _zen_profile_roots():
        if not root.exists():
            continue
        candidates.extend(root.glob("*/cookies.sqlite"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_zen_cookies(domain_name: str = "") -> CookieJar:
    path = _resolve_zen_cookies_path()
    if path is None:
        raise FileNotFoundError(
            "Could not locate Zen Browser cookies.sqlite. Expected to find a Firefox-format "
            "profile under your Zen Browser data directory."
        )
    return browser_cookie3.firefox(cookie_file=str(path), domain_name=domain_name)


_LOADERS: dict[str, Callable[[str], CookieJar]] = {
    "chrome": lambda d: browser_cookie3.chrome(domain_name=d),
    "edge": lambda d: browser_cookie3.edge(domain_name=d),
    "brave": lambda d: browser_cookie3.brave(domain_name=d),
    "firefox": lambda d: browser_cookie3.firefox(domain_name=d),
    "zen": lambda d: _load_zen_cookies(domain_name=d),
    "safari": lambda d: browser_cookie3.safari(domain_name=d),
}


def _hostname_of(base_url: str) -> str:
    host = urlparse(base_url).hostname
    if not host:
        raise ValueError(f"base_url has no hostname: {base_url}")
    return host


def _cookie_matches_host(cookie_domain: str, host: str) -> bool:
    cd = cookie_domain.lstrip(".")
    if not cd:
        return False
    return host == cd or host.endswith("." + cd)


def _serialise_cookie(c: Cookie) -> dict:
    return {
        "name": c.name,
        "value": c.value or "",
        "domain": c.domain,
        "path": c.path or "/",
        "expires": float(c.expires) if c.expires is not None else None,
    }


def _filter_cookies(jar: CookieJar, host: str) -> list[Cookie]:
    return [c for c in jar if _cookie_matches_host(c.domain, host)]


def _try_loader(name: str, host: str) -> list[Cookie]:
    loader = _LOADERS[name]
    jar = loader(host)
    return _filter_cookies(jar, host)


def _format_loader_errors(errors: dict[str, Exception]) -> str:
    if not errors:
        return ""
    parts = [f"{name}: {exc}" for name, exc in errors.items()]
    return " Loader errors — " + "; ".join(parts) + "."


def _write_storage_state(storage_state_path: Path, cookies: list[Cookie]) -> None:
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cookies": [_serialise_cookie(c) for c in cookies],
        "origins": [],
    }
    storage_state_path.write_text(json.dumps(payload, separators=(",", ":")))
    try:
        os.chmod(storage_state_path, 0o600)
    except OSError:
        pass


def import_browser_cookies(
    *,
    base_url: str,
    storage_state_path: Path,
    browser: str = DEFAULT_BROWSER,
) -> dict:
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(
            f"Unsupported browser '{browser}'. Choose one of: {', '.join(SUPPORTED_BROWSERS)}."
        )

    host = _hostname_of(base_url)

    if browser == "auto":
        errors: dict[str, Exception] = {}
        picked: tuple[str, list[Cookie]] | None = None
        for name in _AUTO_ORDER:
            try:
                cookies = _try_loader(name, host)
            except Exception as exc:
                errors[name] = exc
                continue
            if cookies:
                picked = (name, cookies)
                break
        if picked is None:
            raise NoCookiesFoundError(
                f"No Superset session found for {host} in any supported browser. "
                f"Sign in to {base_url} in your browser first, then re-run."
                f"{_format_loader_errors(errors)}"
            )
        browser_used, cookies = picked
    else:
        try:
            cookies = _try_loader(browser, host)
        except Exception as exc:
            raise NoCookiesFoundError(
                f"No Superset session found for {host} in {browser}. "
                f"Sign in to {base_url} in {browser} first, then re-run. "
                f"Loader error — {browser}: {exc}."
            ) from exc
        if not cookies:
            raise NoCookiesFoundError(
                f"No Superset session found for {host} in {browser}. "
                f"Sign in to {base_url} in {browser} first, then re-run."
            )
        browser_used = browser

    _write_storage_state(storage_state_path, cookies)

    return {"browser_used": browser_used, "cookie_count": len(cookies)}
