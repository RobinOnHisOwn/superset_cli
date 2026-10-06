import json
import math
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
_PERSISTED_COOKIE_HINT = (
    " No matching persisted cookie was exposed. A Firefox/Zen session existing only in memory "
    "is possible, but this CLI cannot detect it. Use an accessible session in a supported "
    "browser such as Chrome, validate it once, or report authentication blocked."
)
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
        "secure": bool(c.secure),
        "httpOnly": c.has_nonstandard_attr("HTTPOnly") or c.has_nonstandard_attr("HttpOnly"),
        "sameSite": c.get_nonstandard_attr("SameSite", "Lax"),
    }


def export_playwright_state(source: Path, output: Path, *, expiry_unit: str = "seconds") -> Path:
    if expiry_unit not in {"seconds", "milliseconds"}:
        raise ValueError("Expiry unit must be seconds or milliseconds.")
    payload = json.loads(source.read_text())
    if not isinstance(payload, dict) or not isinstance(payload.get("cookies"), list) or not isinstance(payload.get("origins", []), list):
        raise ValueError("Invalid saved browser state.")
    cookies = []
    for cookie in payload["cookies"]:
        if not isinstance(cookie, dict) or any(not isinstance(cookie.get(key), str) for key in ("name", "value", "domain", "path")):
            raise ValueError("Invalid cookie fields in saved state.")
        expiry = cookie.get("expires")
        if isinstance(expiry, bool) or (expiry is not None and not isinstance(expiry, (int, float))):
            raise ValueError("Invalid cookie expiry in saved state.")
        if expiry is None or expiry in {0, -1}:
            expiry = -1
        else:
            expiry = expiry / (1000 if expiry_unit == "milliseconds" else 1)
            if not math.isfinite(expiry) or not 0 < expiry <= 253402300799:
                raise ValueError("Invalid cookie expiry; select the correct --expiry-unit.")
        item = {key: cookie[key] for key in ("name", "value", "domain", "path")}
        for key in ("secure", "httpOnly"):
            if key in cookie and not isinstance(cookie[key], bool):
                raise ValueError("Invalid cookie attributes in saved state.")
            item[key] = cookie.get(key, False)
        item["sameSite"] = cookie.get("sameSite", "Lax")
        if item["sameSite"] not in {"Strict", "Lax", "None"}:
            raise ValueError("Invalid sameSite cookie attribute.")
        item["expires"] = expiry
        cookies.append(item)
    encoded = json.dumps({"cookies": cookies, "origins": payload.get("origins", [])}, allow_nan=False)
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as destination:
        destination.write(encoded)
    return output


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
    validate: Callable[[Path], bool] | None = None,
) -> dict:
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(
            f"Unsupported browser '{browser}'. Choose one of: {', '.join(SUPPORTED_BROWSERS)}."
        )

    host = _hostname_of(base_url)

    def accepted(cookies: list[Cookie]) -> bool:
        _write_storage_state(storage_state_path, cookies)
        return validate is None or validate(storage_state_path)

    if browser == "auto":
        errors: dict[str, Exception] = {}
        rejected: list[str] = []
        picked: tuple[str, list[Cookie]] | None = None
        for name in _AUTO_ORDER:
            try:
                cookies = _try_loader(name, host)
            except Exception as exc:
                errors[name] = exc
                continue
            if cookies and accepted(cookies):
                picked = (name, cookies)
                break
            if cookies:
                rejected.append(name)
        if picked is None:
            if rejected:
                shutil.rmtree(storage_state_path.parent, ignore_errors=True)
                raise NoCookiesFoundError(
                    f"Superset rejected cookies from: {', '.join(rejected)}. "
                    f"Sign in to {base_url} in another browser, then re-run."
                )
            raise NoCookiesFoundError(
                f"No Superset session found for {host} in any supported browser. "
                f"Sign in to {base_url} in your browser first, then re-run."
                f"{_format_loader_errors(errors)}"
                f"{_PERSISTED_COOKIE_HINT if len(errors) < len(_AUTO_ORDER) else ''}"
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
                f"{_PERSISTED_COOKIE_HINT if browser in {'firefox', 'zen'} else ''}"
            )
        if not accepted(cookies):
            shutil.rmtree(storage_state_path.parent, ignore_errors=True)
            raise NoCookiesFoundError(
                f"A cookie was found in {browser}, but Superset rejected it. "
                "The imported auth state was removed."
            )
        browser_used = browser

    return {"browser_used": browser_used, "cookie_count": len(cookies)}
