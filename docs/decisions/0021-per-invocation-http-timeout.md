# 0021: Per-invocation HTTP timeout

- Status: accepted
- Date: 2026-10-06
- Related: [plan](../plans/2026-10-06-http-timeout.md), `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `src/superset_cli/jwt_auth.py`, `tests/test_timeout.py`

## Context

Slow chart-data and SQL requests need a longer timeout without replacing the authenticated client or bypassing CSRF handling. Existing commands use 30 seconds. Bounded authentication recovery and no sent-mutation retries remain required by [ADR 0011](0011-custom-api-authentication.md) and [ADR 0018](0018-per-instance-jwt-auth.md).

## Decision

Expose one root `--timeout SECONDS` option before the command. Validate finite positive values before browser/network access, retain the 30-second default, and apply the value to every HTTP client created by that invocation, including authentication and CSRF requests.

Use HTTPX connect/read/write/pool phase/inactivity timeout semantics, not a total command deadline. A context-local value, reset when the invocation closes, avoids changing every command signature or leaking settings between invocations. Direct JWT clients receive the value explicitly. Do not persist it or add retries.

Timeouts exit non-zero with a bounded stderr diagnostic. When the timed-out request was a mutation, report that its outcome is unknown and advise checking server state before retrying. Do not echo exception contents or replay the request.

## Consequences

Users can accommodate slow requests while preserving auth handling and write guards. A continuously progressing command can run longer than the timeout. A total deadline would require a separate design. Context-local configuration must be reset even on command failure; tests cover custom/default invocations and request timeout metadata.

## Alternatives considered

### Per-command options

Rejected: duplicated declarations and forwarding across dozens of handlers make auth/CSRF coverage easy to miss.

### Persistent instance configuration

Rejected: this ticket requests an explicit per-invocation override; persistence hides a previous operator's choice.

### Total runtime deadline or automatic retries

Rejected: neither is provided by a scalar HTTPX timeout, and retrying mutations can duplicate writes.
