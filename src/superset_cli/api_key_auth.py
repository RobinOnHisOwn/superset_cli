"""Environment-only API keys; never persist or echo credential values."""
import os
import re

from superset_cli.models import APIKeySettings


def read_api_key(settings: APIKeySettings) -> str:
    key = os.environ.get(settings.env, "")
    if (not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", key)
            or not key.startswith(settings.prefix) or len(key) <= len(settings.prefix)):
        raise ValueError("API key environment variable is missing or invalid; check the configured binding and server prefix.")
    return key
