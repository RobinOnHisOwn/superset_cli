# Design: read-only export commands

## Context

Superset exposes `GET /api/v1/{resource}/export/?q=...` endpoints for several read-only asset types. Each returns a ZIP archive (binary). The CLI today only emits JSON or short human summaries; it has no binary or file-destination handling. This is a design ticket: no implementation in this workstream.

## Endpoints in scope

The four most useful asset exports for an agent inspecting an instance:

- `GET /api/v1/dashboard/export/?q=!(<ids>)` → dashboards as a ZIP
- `GET /api/v1/chart/export/?q=!(<ids>)` → charts as a ZIP
- `GET /api/v1/dataset/export/?q=!(<ids>)` → datasets as a ZIP
- `GET /api/v1/database/export/?q=!(<ids>)` → database connection definitions as a ZIP (Superset's export omits credentials in `export` mode; full credentials require a separate endpoint not covered here)

The `q` argument is a rison-encoded list of IDs.

## Proposed CLI contract

- Subcommands live under existing resource groups:
  - `dashboards export <instance> <id...>`
  - `charts export <instance> <id...>`
  - `datasets export <instance> <id...>`
  - `databases export <instance> <id...>`
- Output handling:
  - `--output <path>` is required; the CLI writes the ZIP bytes to that path.
  - There is no `--json` mode for export; the payload is intentionally binary.
  - If `<path>` exists, fail unless `--force` is supplied. Default behavior is non-destructive.
  - Validate the response `Content-Type` is `application/zip` (or `application/octet-stream` with a zip magic header) before writing; on mismatch, error and do not write the file.
- Multiple IDs:
  - At least one ID required.
  - The CLI rison-encodes the list before sending; callers do not construct `q` manually.
- Error handling reuses existing `_api_errors()` behavior: 401, 404, network, HTTPStatusError.

## Risks

- Client changes: today `SupersetClient._get` only handles JSON responses (it calls `response.json()`). A binary path will need a separate method that returns raw bytes plus the relevant headers. This is the first non-JSON read path and should be added carefully to avoid breaking the existing `AuthExpiredError`-on-non-JSON fallback.
- Auth detection on binary responses: the current "non-JSON response → AuthExpiredError" heuristic protects against silent HTML login redirects. The binary path needs an equivalent check, ideally by validating the status code and content-type before attempting to read the body, since a redirected HTML body is not a zip.
- JSON-output contract: keeping export commands `--output`-only avoids any conflict with the established `--json` contract.
- Rison dependency: rison is not a stdlib module. Options: depend on `prison` (PyPI), hand-roll a minimal encoder for lists of ints, or use a thin lambda. A hand-rolled encoder is simplest and avoids a new dependency.
- File-system safety: writing to arbitrary paths is acceptable for a CLI but must be paired with the no-overwrite default and clear `--force` semantics.

## Recommended follow-up

Create a single follow-up implementation ticket that covers all four export commands with the contract above. Splitting them across four tickets duplicates the binary-handling work in `SupersetClient`.

Follow-up ticket: `2026-06-06-read-only-export-commands-implementation.md`.

## Decision follow-up

Decision record update required: this is the first non-JSON response handled by `SupersetClient`. Once the follow-up implementation lands, update `docs/decisions/` with a new record documenting how the client distinguishes JSON, binary, and auth-redirected responses.
