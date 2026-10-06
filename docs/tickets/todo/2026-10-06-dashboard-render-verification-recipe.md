# Supply one runnable dashboard rendering verification recipe

- Status: todo
- Priority: high
- Type: docs
- Created by: agent
- Created at: 2026-10-06
- Related: `README.md`, `docs/decisions/0008-cookie-extraction-from-installed-browsers.md`, `docs/tickets/todo/2026-10-06-playwright-compatible-auth-state.md`, `docs/tickets/todo/2026-10-06-refresh-companion-skill-recipes.md`

## Context

Recorded usage repeatedly treated successful dashboard/chart API responses as proof of rendering. A blank dashboard was eventually traced to custom CSS hiding the grid, only after executed browser DOM inspection. The companion skill states the right verification gate but agents still have to construct a browser script from scratch.

## Definition of done

- [ ] Provide one copy-pasteable, read-only optional browser recipe accepting an instance/dashboard target and saved auth state, reusing an existing suitable helper where possible.
- [ ] Inspect executed DOM and collect bounded console/page and chart-error evidence; distinguish login, loading timeout, blank content, and successful expected chart/tab rendering.
- [ ] Require expected chart/tab identifiers or counts where applicable; an HTTP 200 or nonempty page alone must not pass.
- [ ] Verify representative tabs and support viewport/inner-container screenshots when needed rather than assuming full-page captures include all content.
- [ ] Document a focused diagnostic sequence: healthy API plus blank DOM leads to comparison with a known-good dashboard, including CSS/theme/metadata; any mutation remains separately authorized and reversible.
- [ ] Run the recipe against a controlled working example and a CSS-hidden failure example and record reproducible results.
- [ ] Keep browser tooling optional and outside default CLI runtime dependencies; update the authoritative companion skill with a pointer to the recipe.

## Notes

This is a verification recipe, not a new rendering service, MCP wrapper, or default browser-login flow. A missing required browser check must report blocked, not success.
