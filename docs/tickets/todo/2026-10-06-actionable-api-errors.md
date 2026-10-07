# Report actionable, sanitized API failure details

- Status: todo
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-06
- Related: `src/superset_cli/cli.py`, `src/superset_cli/client.py`, `tests/test_api.py`, `docs/tickets/done/2026-06-06-superset-client-http-error-mapping.md`

## Context

Verified in source: generic HTTP failures are reduced to `Superset API error: HTTP <status>`. Recorded usage showed agents retrying SQL and constructing replacement HTTP clients to learn why requests failed. CSRF rejection, invalid payloads, and permission failures need distinct actionable evidence.

## Definition of done

- [ ] Report HTTP method, sanitized instance-relative path, status, and bounded useful server error details through the shared error handler on stderr.
- [ ] Handle JSON, plain text, empty, and HTML error responses without a secondary parsing failure.
- [ ] Never expose cookie/header values, credentials, request bodies, or sensitive query parameters; sanitize and bound server-provided details.
- [ ] Preserve successful stdout JSON contracts and nonzero failure exits; retain appropriate existing auth/not-found handling.
- [ ] Test CSRF-related 400, validation 400, auth 401, permission 403, and non-JSON server errors with synthetic responses and secret-redaction assertions.
- [ ] Update troubleshooting documentation so agents use reported evidence instead of repeated identical retries.

## Notes

Do not infer that every HTTP 400 is CSRF-related or every HTTP 403 requires login. Do not introduce automatic mutation retries.
