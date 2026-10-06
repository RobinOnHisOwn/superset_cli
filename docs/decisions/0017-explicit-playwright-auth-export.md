# 0017: Explicit Playwright auth-state export

- Status: accepted
- Date: 2026-10-06
- Related: [continuation plan](../plans/2026-10-06-autonomous-todos-continuation.md), `src/superset_cli/auth.py`, `tests/test_playwright_export.py`

## Context

Browser-cookie state is sufficient for HTTP requests but its expiry convention can prevent Playwright context creation. Browser loaders and externally supplied state must not be conflated. Core login must remain independent of Playwright.

## Decision

Provide optional `auth export-playwright`, requiring an explicit seconds/milliseconds convention. Normalize absent/nonpositive session expiry to -1, reject malformed values, retain available cookie attributes, and create a new private 0600 file exclusively. Do not overwrite or change the CLI state or reopen browser databases. Playwright remains an optional recipe dependency.

The optional dashboard helper requires inspected rendered-content selectors and can check representative tabs and capture viewport/container screenshots. HTTP success, persistence, screenshots, and data correctness are not by themselves render acceptance.

## Consequences

Operators must verify the source convention; browser-cookie3 0.20.1 Chromium/Firefox/Safari loaders use seconds. Exported state and screenshots remain sensitive. Synthetic browser evidence proves the helper, not live acceptance. Incorrect selectors or inaccessible auth fail/are blocked, rather than claiming success.

## Alternatives considered

### Normalize the CLI auth state automatically

Would silently change a shared artifact and hide the source convention.

### Require Playwright for all login/API calls

Would add a runtime dependency and browser lifecycle to workflows that only need installed-browser cookies.
