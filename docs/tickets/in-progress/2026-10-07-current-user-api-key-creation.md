# Create current-user API keys with explicit pipeline output

- Status: in-progress
- Priority: high
- Type: code
- Created by: agent
- Created at: 2026-10-07
- Scope correction: PR 11 delegates storage to the caller; mandatory 1Password handling in the initial PR 12 change is superseded.
- Related: [plan](../../plans/2026-10-08-pr12-pipeline-issuance.md), [ADR 0025](../../decisions/0025-current-user-api-key-creation.md), [lifecycle](2026-10-07-api-key-lifecycle.md), [service-user output](../todo/2026-10-07-secret-safe-key-issuance.md)

## Context

Native FAB creates only for the authenticated user. This narrower path neither provisions service users nor bypasses the service backend/independent recovery prerequisites. Use existing authorized caller credentials and owner-scoped native metadata.

## Selected scope

`auth api-key create INSTANCE --name NAME --expires-on ISO --operation-id UUID --server-timezone IANA --allow-write --secret-output`

Both opt-ins are required before access. Default and JSON invocations remain secret-free; --json cannot accompany secret mode. Verify active identity/lifecycle grants before issuing and owner-scoped read-back plus unchanged identity before emitting. Explicit successful stdout contains only the key and newline; stderr contains safe recovery metadata. The shell owns storage and pipeline status checking. No 1Password dependency, files, raw-key arguments, environment propagation, cross-user target or scopes authorization.

## Definition of done

- [x] Current requirements researched and source-verified; written correction plan and failing tests.
- [x] Literal write/secret guards, TLS and option validation before credential access.
- [x] Verify active identity/grants, before-image, native owner-only GET, identity continuity and stored expiry before output.
- [x] Empty failed/default stdout; explicit successful secret-only output, safe stderr and unchanged auth bindings.
- [x] Attempt verified compensation on HTTP/validation/output failure, partial writes, broken pipes and caught interruption; no mutation replay or downstream storage claim.
- [x] 128 focused tests and 1,072 full tests passed on both supported Python versions (13 skipped each); color/no-color help, manual guard, build/packages and documentation checks recorded in the plan. Read-only conflict preview is clean.
- [ ] Authorized isolated Superset ownership/expiry/rejection acceptance. No target supplied; do not close or release based on mocks alone.

## Decision follow-up

Decision record update required: ADRs 0010, 0023 and replacement 0025; keep service-user research, output and acceptance gates separate.
