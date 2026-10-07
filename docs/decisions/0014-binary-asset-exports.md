# 0014: Explicit binary asset exports

- Status: accepted
- Date: 2026-10-06
- Related: `docs/plans/2026-10-06-autonomous-todos.md`, `docs/plans/2026-06-06-read-only-export-commands.md`, `tests/test_exports.py`

## Context

Asset export endpoints return ZIP archives, unlike the JSON responses consumed by ordinary reads. Treating successful binary content as JSON would falsely report an expired session.

## Decision

Use a separate `_get_binary` helper returning bytes, content type, and status. On non-success responses, delegate to the existing response handler to preserve HTTP/auth/not-found behavior. Do not follow redirects for binary exports. Ordinary JSON methods remain unchanged.

Only dashboard, chart, dataset, and database exports are supported. Encode positive integer ID lists as Rison `!(7,8)` without a dependency. Require `--output`; there is no binary stdout or JSON export mode. Validate an allowed ZIP content type and a ZIP central directory before opening the destination. Open new destinations exclusively by default, including against races; `--force` explicitly permits replacement. Local write errors return nonzero. Database exports remain sensitive even when server export mode omits credentials.

## Consequences

A successful HTML or JSON response cannot be written as an archive. No live mutation is involved. Exports are held in memory and writing with `--force` is not transactional; operators should use a new destination when preserving an existing archive matters.

## Alternatives considered

### Add binary handling to every JSON request

Rejected: separate explicit helpers keep existing output and auth contracts stable.

### Add a Rison dependency

Rejected: encoding a validated list of integers requires only joining their decimal representations.
