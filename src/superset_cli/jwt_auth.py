"""Direct DB/LDAP JWT authentication, separate from browser cookie state."""
import base64
import json
import math
import os
import re
import tempfile
from pathlib import Path
from ipaddress import ip_address
from urllib.parse import urlsplit

import httpx


def require_jwt_tls(base_url) -> None:
    parts = urlsplit(str(base_url))
    if parts.username is not None or parts.password is not None:
        raise ValueError("JWT base URLs must not contain embedded credentials.")
    if parts.scheme == "https" and parts.hostname:
        return
    if parts.scheme == "http":
        if parts.hostname in {"localhost", "localhost."}:
            return
        try:
            if ip_address(parts.hostname or "").is_loopback:
                return
        except ValueError:
            pass
    raise ValueError("JWT requires HTTPS; HTTP is allowed only for loopback development.")


def _valid_bearer(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", value) is not None


def load_jwt_state(path: Path) -> dict:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or payload.get("mode") != "jwt" or any(not _valid_bearer(payload.get(key)) for key in ("access_token", "refresh_token")):
        raise ValueError("Invalid saved JWT state.")
    return {"mode":"jwt", "access_token":payload["access_token"], "refresh_token":payload["refresh_token"]}


def save_jwt_state(path: Path, state: dict) -> None:
    if not isinstance(state, dict) or any(not _valid_bearer(state.get(key)) for key in ("access_token", "refresh_token")):
        raise ValueError("JWT response omitted or malformed required tokens.")
    encoded = json.dumps({"mode":"jwt", "access_token":state["access_token"], "refresh_token":state["refresh_token"]})
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".jwt-state-", delete=False) as destination:
            staging = Path(destination.name)
            destination.write(encoded)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(staging, path)
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


def login_jwt(base_url: str, path: Path, *, username: str, password: str, provider: str = "db") -> None:
    if provider not in {"db", "ldap"} or not username or not password:
        raise ValueError("JWT requires credentials and provider db or ldap.")
    require_jwt_tls(base_url)
    with httpx.Client(base_url=base_url.rstrip("/"), follow_redirects=False, timeout=30) as http:
        response = http.post("/api/v1/security/login", json={"username":username,"password":password,"provider":provider,"refresh":True})
        response.raise_for_status()
        save_jwt_state(path, response.json())


def refresh_jwt(http: httpx.Client, path: Path) -> dict:
    require_jwt_tls(http.base_url)
    state = load_jwt_state(path)
    response = http.post("/api/v1/security/refresh", headers={"Authorization":f"Bearer {state['refresh_token']}"}, follow_redirects=False)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str) or not payload["access_token"]:
        raise ValueError("JWT refresh response omitted its access token.")
    state["access_token"] = payload["access_token"]
    save_jwt_state(path, state)
    return state


def token_expiry(token: str) -> int | float | None:
    # The unverified claim is display-only; authentication is always server-validated.
    try:
        part = token.split(".")[1]
        if len(part) > 8192:
            return None
        value = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))["exp"]
        return value if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else None
    except (ValueError, IndexError, KeyError, TypeError):
        return None


def jwt_status(path: Path) -> dict:
    state = load_jwt_state(path)
    return {"mode":"jwt", "authenticated":True, "access_token_exp":token_expiry(state["access_token"]), "refresh_token_exp":token_expiry(state["refresh_token"])}
