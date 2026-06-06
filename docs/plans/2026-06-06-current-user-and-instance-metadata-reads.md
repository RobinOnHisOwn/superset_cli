# Current-user and instance metadata reads

## Goal

Expose a small `me` command group for lightweight introspection of the authenticated user and their roles against a configured Superset instance.

## Scope

- `me show <instance>` → calls `/api/v1/me/`, returns the current user.
- `me roles <instance>` → calls `/api/v1/me/roles/`, returns the user's roles.

Stay strictly read-only. Do not add user-creation, permission-management, or menu/configuration endpoints in this ticket.

## API references

- `GET /api/v1/me/` — already used by `auth validate`; payload is `{"result": {...user...}}`.
- `GET /api/v1/me/roles/` — payload is `{"result": {...user-with-roles...}}` per Superset's `CurrentUserRestApi`.

Both responses use the standard `result` wrapper; the client should unwrap them.

## Plan

1. Add `get_current_user_roles()` to `SupersetClient` that unwraps `result`.
2. Add an `me_app` Typer group in `cli.py` registered as `me`.
3. Add `me show` (`/api/v1/me/`) reusing `client.get_current_user()`.
4. Add `me roles` (`/api/v1/me/roles/`) calling the new helper.
5. Human output:
   - `show`: `User: {username}` and `Name: {first_name} {last_name}` (trimmed if missing).
   - `roles`: one role name per line, or `No roles assigned.` if empty.
6. JSON output returns the raw payload unchanged.
7. Standard guard paths: unknown instance, missing saved state, network error, HTTPStatusError (now handled centrally), auth-expired, not-found.

## Tests

- Unit test for `SupersetClient.get_current_user_roles()` unwrapping `result`.
- CLI tests in `tests/test_me.py`:
  - unknown instance
  - missing saved state
  - JSON output for `show` and `roles`
  - human output for `show` and `roles`
  - empty roles message
  - auth expired
  - network error
  - client closure

## Decision follow-up

No durable decision change. Stays within the existing read-only bootstrap scope documented in `docs/decisions/0001-read-only-bootstrap-scope.md`.
