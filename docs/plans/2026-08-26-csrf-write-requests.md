# Send CSRF tokens with Superset write requests

**Date:** 2026-08-26

## Goal

Make existing opt-in write commands work against Superset instances that enforce CSRF protection.

## Planned changes

1. Add a failing client test proving POST, PUT, and DELETE requests fetch `/api/v1/security/csrf_token/` and send its result as `X-CSRFToken`.
2. Cache the token per `SupersetClient` instance so a sequence of writes does not refetch it.
3. Preserve the existing literal `--allow-write` CLI guard unchanged.
4. Update the architecture reference to describe CSRF handling on write requests.

## Verification

- `uv run pytest tests/test_client.py -v`
- `uv run pytest -v`
- `uv run superset-cli --help`
- `uv build`
- Retry one staging dataset create with literal `--allow-write`.

## Decision follow-up

No durable decision change. This implements Superset's required request protocol within the already-approved write surface.
