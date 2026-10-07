# Add API-key auth support for supported Superset versions

- Status: done
- Priority: low
- Type: code
- Created by: agent
- Created at: 2026-06-06
- Related: [corrected research](../../plans/2026-06-06-api-key-auth-design.md), [plan](../../plans/2026-10-06-remaining-open-todos.md), [ADR 0023](../../decisions/0023-environment-bound-api-keys.md), `tests/test_api_key_auth.py`

## Corrected prerequisite evidence

Superset 6.1.0 inherits FAB's concrete SQLA SecurityManager. FAB 5.2.2 implements API-key verification and blueprint registration. The earlier assumption that it must reach the abstract `NotImplementedError` was incorrect; the research now records concrete inheritance and version-pinned source links.

The verified combination still requires `FAB_API_KEY_ENABLED=True`, initialized key storage, an active issued key, a matching prefix, and sufficient RBAC. Superset's version alone is not sufficient. No real target/key was tested in this task; the CLI validates a read before saving an environment binding, so unsupported/rejected deployments fail safely.

## Definition of done

- [x] Confirm version-specific protocol support and correct the previous research assumption.
- [x] Add explicit per-instance environment-only API-key config/client/CLI support.
- [x] API-backed workflows do not require browser state in API-key mode; use one shared client factory.
- [x] Test binding/clear/status, missing/malformed secrets, custom prefixes, rotation, HTTPS, redirects, rejected auth, CSRF, write guards, and no sent-write retries.
- [x] Update README, architecture, and durable decision record with actual version/configuration limits.

## Completion evidence

Initial API-key tests failed on the absent command. Mocked red/green checks cover reads and writes without live Superset mutations. Keys never enter config/state/output; only environment names and prefixes are saved after successful acceptance. Cookie/JWT state is preserved, and browser logout cannot delete it inadvertently while API-key mode is selected. No key-management endpoint, server upgrade, dependency, or browser fallback was added. Full verification is recorded in the linked plan.
