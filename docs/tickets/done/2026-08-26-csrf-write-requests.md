# Send CSRF tokens with write requests

- Status: done
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-08-26
- Related: `docs/plans/2026-08-26-csrf-write-requests.md`, `docs/decisions/0009-write-command-explicit-opt-in.md`, `docs/decisions/0010-write-scope-expansion.md`, `src/superset_cli/client.py`, `tests/test_client.py`

## Context

Live staging returned HTTP 400 with `The CSRF token is missing` for an explicitly authorized dataset create. The client sends browser cookies but does not fetch Superset's CSRF token or attach `X-CSRFToken` to write requests.

## Definition of done

- [x] POST, PUT, and DELETE send a valid CSRF header and same-origin referrer.
- [x] The token is cached for the client lifetime.
- [x] Existing write guards remain unchanged.
- [x] Focused and full verification pass.

## Notes

The original failing staging request created no object. Live verification then created migration-owned dataset 970 successfully with literal `--allow-write`.
