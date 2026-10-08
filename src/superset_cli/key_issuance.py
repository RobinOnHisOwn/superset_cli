"""Current-user issuance with captured 1Password delivery and best-effort rollback."""

import hmac
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from superset_cli.api_key_auth import validate_api_key
from superset_cli.client import HTTP_TIMEOUT, SupersetClient
from superset_cli.models import APIKeySettings


def creation_request(name, expires_on, operation_id, account, vault, prefix, server_timezone):
    try:
        operation_id = str(UUID(operation_id))
        expiry = datetime.fromisoformat(expires_on)
        now = datetime.now(timezone.utc)
        if expiry.utcoffset() is None or not now < expiry <= now + timedelta(days=90):
            raise ValueError()
        for value in (name, account, vault):
            if (not value or value != value.strip() or value.startswith("-")
                    or any(ord(char) < 32 or ord(char) == 127 for char in value)):
                raise ValueError()
        if len(name) > 180:
            raise ValueError()
        APIKeySettings(env="UNUSED", prefix=prefix)
        zone = ZoneInfo(server_timezone)
        expiry = expiry.astimezone(zone).replace(tzinfo=None)
        if expiry.replace(tzinfo=zone, fold=0).utcoffset() != expiry.replace(tzinfo=zone, fold=1).utcoffset():
            raise ValueError()  # FAB's naive DateTime cannot represent a DST fold.
    except (ValueError, TypeError, AttributeError, ZoneInfoNotFoundError):
        raise ValueError("Invalid creation options: use a UUID, explicit name/account/vault/server timezone and a timezone-aware future expiry within 90 days, outside a DST fold.") from None
    return {"name": f"{name} [{operation_id}]", "expires_on": expiry.isoformat()}, operation_id


def create_and_store_key(client: SupersetClient, *, body, operation_id, account, vault, prefix, server_timezone):
    result = {"operation_id": operation_id, "key_uuid": None, "item_id": None,
              "vault_id": None, "stored": False, "revocation_verified": None,
              "outcome": "preflight_failed", "item_cleanup": "not_needed"}
    # Exclude caller credentials even when aliased under allowed op variable names.
    caller_secrets = {cookie.value for cookie in client.storage_state.cookies}
    caller_secrets.add(client.http.headers.get("Authorization", "").partition(" ")[2])
    env = {key: value for key, value in os.environ.items()
           if value not in caller_secrets and (
               key in {"PATH", "HOME", "USER", "LANG", "TMPDIR", "XDG_CONFIG_HOME"}
               or key in {"OP_SERVICE_ACCOUNT_TOKEN", "OP_CONNECT_HOST", "OP_CONNECT_TOKEN", "OP_CONFIG_DIR"}
               or key.startswith("OP_SESSION_"))}

    def op(args, payload=None, raw=False):
        argv = ["op", *args]
        if not raw:
            argv += ["--account", account, "--format", "json", "--cache=false"]
        completed = subprocess.run(argv, input=json.dumps(payload) if payload is not None else None,
                                   capture_output=True, text=True, timeout=HTTP_TIMEOUT.get(), env=env)
        if completed.returncode:
            raise ValueError("1Password operation failed.")
        return completed.stdout.strip() if raw else json.loads(completed.stdout or "{}")

    def identifier(value):
        if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9]{26}", value):
            raise ValueError("Invalid 1Password identifier.")
        return value

    def item_fields(item):
        if item.get("id") != result["item_id"] or item.get("vault", {}).get("id") != result["vault_id"]:
            raise ValueError("1Password destination mismatch.")
        fields = item["fields"]
        if not isinstance(fields, list) or any(not isinstance(field, dict) for field in fields):
            raise ValueError("Invalid 1Password fields.")
        values = {field["id"]: field.get("value", "") for field in fields}
        if (len(values) != len(fields) or values.get("operation_id") != operation_id
                or not any(field.get("id") == "credential" and field.get("type") == "CONCEALED" for field in fields)):
            raise ValueError("1Password operation or credential-field mismatch.")
        return values

    def get_item():
        return op(["item", "get", result["item_id"], "--vault", result["vault_id"], "--reveal"])

    before = set()
    sent = False
    item_confirmed = False
    try:
        user = client.get_current_user_roles()
        required = {("can_" + permission, "ApiKey") for permission in ("list", "create", "get", "revoke")}
        required.add(("can_read", "SecurityRestApi"))
        permissions = {tuple(pair) for pairs in user["roles"].values() for pair in pairs}
        if type(user.get("userId")) is not int or user["userId"] < 1 or user.get("isActive") is not True or not required <= permissions:
            raise ValueError("Missing active caller or lifecycle permissions.")
        existing = client.list_api_keys()["result"]
        before = {client.validate_api_key_uuid(item["uuid"]) for item in existing}
        if any(item.get("name", "").endswith(f"[{operation_id}]") for item in existing):
            raise ValueError("Operation already exists; reconcile before retrying.")
        if op(["--version"], raw=True) != "2.33.1":
            raise ValueError("This workflow requires the verified op 2.33.1 contract.")
        result["vault_id"] = identifier(op(["vault", "get", vault])["id"])
        fields = {"credential": "pending", "operation_id": operation_id, "superset_key_uuid": "",
                  "superset_owner_id": str(user["userId"]), "superset_url": client.base_url}
        template = {"category": "API_CREDENTIAL", "title": f"Superset key [{operation_id}]",
                    "fields": [{"id": key, "label": key, "type": "CONCEALED" if key == "credential" else "STRING",
                                "value": value} for key, value in fields.items()]}
        result.update(outcome="preflight_unverified", item_cleanup="unverified")
        result["item_id"] = identifier(op(["item", "create", "-", "--vault", result["vault_id"]], template)["id"])
        if item_fields(get_item()).get("credential") != "pending":
            raise ValueError("Placeholder read-back failed.")
        item_confirmed = True
        # Verify edit access on this new item before issuing a usable credential.
        template["fields"][0]["value"] = "preflight"
        op(["item", "edit", result["item_id"], "--vault", result["vault_id"]], template)
        if item_fields(get_item()).get("credential") != "preflight":
            raise ValueError("Placeholder edit verification failed.")
        if datetime.fromisoformat(body["expires_on"]) <= datetime.now(ZoneInfo(server_timezone)).replace(tzinfo=None):
            raise ValueError("Expiry elapsed during preflight.")
        result["outcome"] = "issuance_unverified"
        sent = True  # Conservative if CSRF/network fails before POST; never replay.
        issued = client.request("POST", "/api/v1/security/api_keys/", json_body=body)["result"]
        key_uuid = client.validate_api_key_uuid(issued["uuid"])
        secret = validate_api_key(issued["key"], prefix)
        metadata = client.get_api_key(key_uuid)["result"]
        if key_uuid in before or metadata.get("name") != body["name"] or metadata.get("active") is not True:
            raise ValueError("Issued key identity mismatch.")
        expiry = datetime.fromisoformat(metadata["expires_on"])
        if expiry.tzinfo is not None or expiry != datetime.fromisoformat(body["expires_on"]):
            raise ValueError("Issued key expiry mismatch.")
        result["key_uuid"] = key_uuid
        for field in template["fields"]:
            if field["id"] == "credential":
                field["value"] = secret
            elif field["id"] == "superset_key_uuid":
                field["value"] = key_uuid
        op(["item", "edit", result["item_id"], "--vault", result["vault_id"]], template)
        saved = item_fields(get_item())
        if (saved.get("superset_key_uuid") != key_uuid
                or saved.get("superset_owner_id") != str(user["userId"])
                or saved.get("superset_url") != client.base_url
                or not isinstance(saved.get("credential"), str)
                or not hmac.compare_digest(saved["credential"], secret)):
            raise ValueError("Stored credential verification failed.")
        result.update(stored=True, outcome="stored", item_cleanup="not_needed")
        return result
    except (Exception, KeyboardInterrupt):
        # Never propagate HTTP/subprocess bodies, captured output or exception text.
        if sent:
            try:
                if result["key_uuid"] is None:
                    candidates = [item for item in client.list_api_keys()["result"]
                                  if item.get("name") == body["name"] and item.get("uuid") not in before]
                    if len(candidates) != 1:
                        raise ValueError("Issuance outcome unknown; reconcile operation marker.")
                    result["key_uuid"] = client.validate_api_key_uuid(candidates[0]["uuid"])
                client.revoke_api_key(result["key_uuid"])
                result.update(revocation_verified=True, outcome="delivery_failed_revoked")
            except (Exception, KeyboardInterrupt):
                result.update(revocation_verified=False, outcome="cleanup_unverified" if result["key_uuid"] else "issuance_unverified")
        if item_confirmed and (not sent or result["revocation_verified"] is True):
            try:
                item_fields(get_item())  # Check correlation again before deleting.
                op(["item", "delete", result["item_id"], "--vault", result["vault_id"]])
                result["item_cleanup"] = "requested"  # Not an atomic deletion guarantee.
            except (Exception, KeyboardInterrupt):
                result["item_cleanup"] = "unverified"
        elif result["item_id"]:
            result["item_cleanup"] = "retained"
        return result
