"""Environment-only API keys; never persist or echo credential values."""
import os
import re

from superset_cli.models import APIKeySettings


def validate_api_key(key: str, prefix: str) -> str:
    if (not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", key)
            or not key.startswith(prefix) or len(key) <= len(prefix)):
        raise ValueError("API key environment variable is missing or invalid; check the configured binding and server prefix.")
    return key


def read_api_key(settings: APIKeySettings) -> str:
    return validate_api_key(os.environ.get(settings.env, ""), settings.prefix)
