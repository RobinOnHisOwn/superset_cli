# 0016: Bounded sanitized HTTP failure diagnostics

- Status: accepted
- Date: 2026-10-06
- Related: `docs/plans/2026-10-06-autonomous-todos.md`, `tests/test_api_error_details.py`, `tests/test_dashboards_get.py`

## Context

An HTTP status alone is insufficient to distinguish CSRF rejection, schema validation, and missing permissions. Unbounded server responses can expose request secrets or tracebacks.

## Decision

Generic HTTP errors report method, instance-relative path without query parameters, status, and at most 400 printable characters of selected server details on stderr. Select only JSON `message`, `error`, and `errors`; handle plain text and empty responses; replace HTML with a fixed diagnostic instead of echoing tracebacks.

Redact known request cookie/authorization/query/body values, URL credentials, credential-like assignments, bearer strings, URLs, and terminal control sequences before truncation. Never display headers or request bodies themselves. Keep existing authentication and not-found mappings unchanged; do not infer CSRF from every 400, infer expired auth from every 403, or introduce request retries.

## Consequences

Successful JSON stdout remains unchanged. The generic HTTP failure diagnostic intentionally moves from stdout to stderr. Redaction is conservative and may remove a nonsecret input value from validation messages. Runtime server text must still be treated as sensitive when sharing logs.

## Alternatives considered

### Print the full response and request

Rejected: it can disclose secrets and produces excessive, misleading HTML tracebacks.

### Automatically retry suspected CSRF failures

Rejected: a mutation may already have been sent, and identical retries do not establish the cause.
