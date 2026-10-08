"""Native current-user issuance with explicit output and best-effort compensation."""

import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from superset_cli.api_key_auth import validate_api_key
from superset_cli.models import APIKeySettings


def creation_request(name, expires_on, operation_id, prefix, server_timezone):
    try:
        operation_id = str(UUID(operation_id))
        expiry = datetime.fromisoformat(expires_on)
        now = datetime.now(timezone.utc)
        if expiry.utcoffset() is None or not now < expiry <= now + timedelta(days=90):
            raise ValueError()
        if (not name or name != name.strip() or len(name) > 180
                or any(ord(char) < 32 or ord(char) == 127 for char in name)):
            raise ValueError()
        APIKeySettings(env="UNUSED", prefix=prefix)
        zone = ZoneInfo(server_timezone)
        expiry = expiry.astimezone(zone).replace(tzinfo=None)
        if expiry.replace(tzinfo=zone, fold=0).utcoffset() != expiry.replace(tzinfo=zone, fold=1).utcoffset():
            raise ValueError()
    except (ValueError, TypeError, AttributeError, ZoneInfoNotFoundError):
        raise ValueError("Invalid creation options: use a name, UUID, verified server timezone and timezone-aware future expiry within 90 days, outside a DST fold.") from None
    return {"name": f"{name} [{operation_id}]", "expires_on": expiry.isoformat()}, operation_id


def emit_secret(secret):
    stdout = sys.stdout
    value = secret + "\n"
    try:
        if stdout.write(value) != len(value):
            raise OSError("Incomplete secret stream write.")
        stdout.flush()
    except BrokenPipeError:
        # Python flushes stdout again on exit; prevent a second broken-pipe flush.
        try:
            with open(os.devnull, "w") as sink:
                os.dup2(sink.fileno(), stdout.fileno())
        except (AttributeError, OSError, ValueError):
            pass  # In-memory/test streams do not necessarily have a descriptor.
        raise


def create_and_emit_key(client, *, body, operation_id, prefix, server_timezone):
    result = {"operation_id": operation_id, "key_uuid": None, "owner_id": None,
              "emitted": False, "revocation_verified": None, "outcome": "preflight_failed"}
    before = set()
    sent = False
    try:
        user = client.get_current_user_roles()
        required = {("can_" + perm, "ApiKey") for perm in ("list", "create", "get", "revoke")}
        required.add(("can_read", "SecurityRestApi"))
        permissions = {tuple(pair) for pairs in user["roles"].values() for pair in pairs}
        if type(user.get("userId")) is not int or user["userId"] < 1 or user.get("isActive") is not True or not required <= permissions:
            raise ValueError("Missing active caller or lifecycle grants.")
        result["owner_id"] = user["userId"]
        existing = client.list_api_keys()["result"]
        before = {client.validate_api_key_uuid(item["uuid"]) for item in existing}
        if any(item.get("name", "").endswith(f"[{operation_id}]") for item in existing):
            raise ValueError("Existing operation; reconcile instead of replaying.")
        if datetime.fromisoformat(body["expires_on"]) <= datetime.now(ZoneInfo(server_timezone)).replace(tzinfo=None):
            raise ValueError("Expiry elapsed during preflight.")
        result["outcome"] = "issuance_unverified"
        sent = True  # Conservative even if CSRF retrieval fails before POST.
        issued = client.request("POST", "/api/v1/security/api_keys/", json_body=body)["result"]
        key_uuid = client.validate_api_key_uuid(issued["uuid"])
        secret = validate_api_key(issued["key"], prefix)
        metadata = client.get_api_key(key_uuid)["result"]  # Native GET is owner-only.
        current = client.get_current_user_roles()
        if (key_uuid in before or metadata.get("name") != body["name"] or metadata.get("active") is not True
                or current.get("userId") != user["userId"] or current.get("isActive") is not True):
            raise ValueError("Issued ownership or identity mismatch.")
        expiry = datetime.fromisoformat(metadata["expires_on"])
        if expiry.tzinfo is not None or expiry != datetime.fromisoformat(body["expires_on"]):
            raise ValueError("Issued expiry mismatch.")
        result["key_uuid"] = key_uuid
        emit_secret(secret)
        result.update(emitted=True, outcome="emitted")
    except (Exception, KeyboardInterrupt):
        # HTTP bodies, exceptions and failed stream contents never reach diagnostics.
        if sent:
            try:
                if result["key_uuid"] is None:
                    candidates = [item for item in client.list_api_keys()["result"]
                                  if item.get("name") == body["name"] and item.get("uuid") not in before]
                    if len(candidates) != 1:
                        raise ValueError("Issuance uncertain; reconcile the operation marker.")
                    result["key_uuid"] = client.validate_api_key_uuid(candidates[0]["uuid"])
                client.revoke_api_key(result["key_uuid"])
                result.update(revocation_verified=True, outcome="issuance_failed_revoked")
            except (Exception, KeyboardInterrupt):
                result.update(revocation_verified=False, outcome="cleanup_unverified" if result["key_uuid"] else "issuance_unverified")
    return result
